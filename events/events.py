import pygame
import os
import json
from constants import EVENT_DIR, GameState, Direction
import events.condition_helpers as ch
from typing import TYPE_CHECKING
from objects.map_objects import Node, Map, MapObject, Teleporter
from dialog.dialog_helpers import format_time_of_day
import re
if TYPE_CHECKING:
    from ultimalike import GameEngine

event_funcs = {}

def evention(key):
    def decorator(func):
        event_funcs[key] = func
        return func
    return decorator
class TimerManager:
    def __init__(self):
        self.timers = {}
    
    def start_timer(self, name: str, duration: int | float, is_active: bool = True):
        """Start a new timer"""
        self.timers[name] = {
            'start_time': pygame.time.get_ticks(),
            'duration': duration,
            'active': is_active
        }
    
    def restart_timer(self, name: str):
        if name in self.timers:
            self.timers[name]['start_time'] = pygame.time.get_ticks()
    
    def is_active(self, name):
        """Check if a timer is currently running"""
        if name not in self.timers:
            return False
        return self.timers[name]['active']

    def any_active(self):
        """Check if any timer is currently running"""
        return any(timer['active'] for timer in self.timers.values())
    
    def get_progress(self, name, cancel_if_done: bool = True):
        """Get progress as a percentage (0.0 to 1.0)"""
        if not self.is_active(name):
            return 1.0
        
        timer = self.timers[name]
        elapsed = pygame.time.get_ticks() - timer['start_time']
        progress = min(elapsed / timer['duration'], 1.0)
        
        if progress >= 1.0 and cancel_if_done:
            self.cancel_timer(name)
        
        return progress
    
    def get_remaining_time(self, name, cancel_if_done: bool = True):
        """Get remaining time in milliseconds"""
        if not self.is_active(name):
            return 0
        
        timer = self.timers[name]
        elapsed = pygame.time.get_ticks() - timer['start_time']
        remaining_time = max(0, timer['duration'] - elapsed)
        if remaining_time <= 0 and cancel_if_done:
            self.cancel_timer(name)
        return remaining_time
    
    def cancel_timer(self, name, pop_event_wait: bool = False):
        """Cancel a timer"""
        if name in self.timers:
            if "event_wait" not in name or pop_event_wait:
                self.timers.pop(name)

#These are functions primarily meant to assist in managing quests and movement in in-engine cutscenes
class EventManager:
    def __init__(self, engine: 'GameEngine', flags: set = set(), talked_to_npcs: set = set()):
        self.events = {}
        self.engine = engine
        self.load_event_scripts()
        self.event_master: Node = None
        self.current_event_queue: dict = {}
        self.current_index = -1
        self.force_end = False
        self.looking = False
        self.user_input = ""
        self.last_input = ""
        self.speaker_name = ""
        self.current_line = ""
        self.flags = flags #Track various dialog flags. Needs to be saved
        self.talked_to_npcs = talked_to_npcs
        self.pending_events = {}
        self.delayed_events = {}
        self.timer_manager = TimerManager()
        self.event_duration = 150
        self.timers = {
            "player_move" : 0,
            "event_wait" : 0,
            "teleporter_delay" : 0,
            "event_pause" : 0,
            "player_bump" : 0
        }
        self.timer_limits = {
            "player_move" : 0,
            "event_wait" : 0,
            "player_bump" : 0
        }
        self.waiting_for_input = False
        self.yesno_question = 0
        self.waiting_for_walk = False
        self.make_leader_invisible = False
        self.walk_directions: list[str] = []
        self.walkers: list[MapObject] = []
        self.waiting_timer = 0
        self.wait_timer_limit = 0
        self.event_pause_timer = 0

    def load_event_scripts(self):
        """Load dialog data from dialog.json files"""
        onlyfiles = [f for f in os.listdir(EVENT_DIR) if os.path.isfile(os.path.join(EVENT_DIR, f))]
        for file_name in onlyfiles:
            if file_name.endswith("event.json"):
                with open(os.path.join(EVENT_DIR, file_name), 'r') as f:
                    event_scripts = json.load(f)
                    if event_scripts:
                        for key, value in event_scripts.items():
                            self.events[key] = value
                            
    @evention("start_event")
    def start_event(self, key: str, event_master: Node, force_start: bool = False, treat_as_event: bool = True):
        if key in self.events:
            my_queue = self.events[key]
            conditions = my_queue.get("conditions", [])
            conditions_met = all(self._check_condition(condition) for condition in conditions)
            if conditions_met:
                self.event_master = event_master
                if not self.event_master and self.engine.state == GameState.DIALOG:
                    self.event_master = self.engine.dialog_manager.current_speaker
                flags = my_queue.get("flags", [])
                for flag in flags:
                    self.flags.add(flag)
                if force_start:
                    my_queue["trigger"] = "on_step"
                match my_queue["trigger"]:
                    case "on_step":
                        self.current_event_queue = my_queue
                        if treat_as_event:
                            print(f"{key} is an event")
                            self.engine.change_state(GameState.EVENT)
                        if force_start:
                            my_queue["trigger"] = "after_step"
                    case "after_step":
                        self.delayed_events["event_start"] = key
                        return False
            destroy_trigger_node = my_queue.get("destroy_trigger_object", "")
            trigger_not_relevant = my_queue.get("destroy_even_if_conditions_fail", False)
            if destroy_trigger_node == "on_trigger" and (conditions_met or trigger_not_relevant):
                return True
            elif destroy_trigger_node == "after_trigger" and trigger_not_relevant and not conditions_met:
                return True
        return False
        
    @evention("advance_queue")
    def advance_queue(self):
        if not self.current_event_queue or self.waiting_for_input or self.walkers:
            return
        if self.timer_manager.get_remaining_time("event_pause") > 0:
            return
        self.current_index += 1
        print(f"made it to step {self.current_index}")
        script = self.current_event_queue["script"]
        if self.current_index >= len(script):
            self.end_event()
            return
        line = script[self.current_index]
        lines = line.split("++")
        line = lines[-1]
        conditions = ""
        if len(lines) == 2:
            conditions = lines[0].split("&&")

        if all(self._check_condition(condition) for condition in conditions):
            self._do_event(line)
            
    @evention("end_event")
    def end_event(self):
        self.current_index = -1
        self.engine.revert_state()
        destroy_trigger_node = self.current_event_queue.get("destroy_trigger_object", "")
        em = self.event_master
        if destroy_trigger_node == "after_trigger" and em:
           self.engine.current_map.remove_object(em)
           del em
        keys = []
        for timer in self.timer_manager.timers.keys():
            if "event_wait" in timer:
               keys.append(timer)
        for timer in keys:
            x = self.timer_manager.timers.pop(timer)
            del x
        self.current_event_queue = {}
        self.event_master = None
        self.current_line = ""
        self.waiting_for_input = False

    @evention("give_gold")
    def give_gold(self, gold: int):
        self.engine.party.gold += gold
        return True
    
    @evention("delayed_teleport")
    def delayed_teleport(self, delay_time: int):
        teleporter_here = self.engine.current_map.get_object_by_name(self.pending_events["new_args"]["position"]["from_any"])
        print(self.pending_events["new_args"]["position"]["from_any"])
        print(teleporter_here)
        teleporter_here.args = self.pending_events["new_args"]
        self.pending_events = {}
        self.delayed_events = {"teleporter" : teleporter_here}
        self.timer_manager.start_timer("teleporter_delay", delay_time)

    @evention("start_cutscene")
    def start_cutscene(self, line: str):
        self.engine.cutscene_manager.start_scene(line)
    
    @evention("move_object_to")
    def move_object_to(self, obj: Node, new_pos: tuple[int, int] = (0, 0), new_map: Map = None):
        if new_map:
            if obj.map != new_map:
                obj.map.remove_object(obj)
            obj.map = new_map
            new_map.add_object(obj)
        if not (0 <= new_pos[0] < len(obj.map.tiles[0]) or 0 <= new_pos[1] < len(obj.map.tiles)):#Give an error if trying to move object out of bounds
            raise IndexError
        obj.position = new_pos
        return True
    
    def initialize_walk(self, instructions: str):
        instruction_set = re.split(r'(alternate|N|E|S|W)', instructions)
        if instruction_set[1] == "alternate":
            #Ex. "alternateNE3": move north then east, three times
            count = int(instruction_set[-1])
            direcs = ""
            for _ in range(count):
                for direc in instruction_set[2:-1]:
                    direcs += direc
            self.walk_directions.append(direcs)
        else:
            i = 1
            direcs = ""
            while i < len(instruction_set):
                direc = instruction_set[i]
                count = int(instruction_set[i+1])
                for _ in range(count):
                    direcs += direc
                i += 2
            self.walk_directions.append(direcs)
        
    def continue_walk(self, ignore_walls: bool = True):
        if not self.walk_directions:
            for i, obj in enumerate(self.walkers):
                timer_name = f"event_wait_{obj.name}"
                self.timer_manager.cancel_timer(timer_name, True)
            self.walkers = []
            return
            
        walk_complete = []
        for i, obj in enumerate(self.walkers):
            timer_name = f"event_wait_{obj.name}"
            progress = self.timer_manager.get_progress(timer_name, False)
            if progress < 1.0:
                continue
            self.timer_manager.restart_timer(timer_name)
            self.engine.current_map.generation += 1
            if not self.walk_directions[i]:
                walk_complete.append(i)
                obj.old_position = obj.position
                continue
            direc = self.engine.get_direction(self.walk_directions[i][0])
            tpos = obj.add_tuples(obj.position, direc.value)
            self.walk_directions[i] = self.walk_directions[i][1:]
            if obj.map.is_passable(tpos) or ignore_walls:
                obj.old_position = obj.position
                obj.position = tpos
                obj.last_move_direction = direc.value
        for i in reversed(walk_complete):
            self.timer_manager.cancel_timer(f"event_wait_{self.walkers[i].name}", True)
            self.walkers.pop(i)
            self.walk_directions.pop(i)
    
    @evention("set_flag")
    def set_flag(self, line: str):
        for flag in line.split("&&"):
            self.flags.add(flag)
    
    @evention("del_flag")
    def del_flag(self, line: str):
        for flag in line.split("&&"):
            if flag in self.flags:
                self.flags.remove(flag)
    
    @evention("add_item")
    def add_item(self, line: str):
        quantity = 1
        if "__" in line:
            line, quantity = line.split("__")
        self.engine.party.add_item_by_name(line, quantity)

    @evention("jump")
    def jump(self, num: int):
        if self.engine.state == GameState.EVENT:
            self.current_index += num
        elif self.engine.state == GameState.DIALOG:
            self.engine.dialog_manager.current_line_index += num

    @evention("text")
    def text(self, line: str):
        speaker, line = line.split("__")
        self.waiting_for_input = True
        if "--dai" in line:#shorthand for don't await input
            self.waiting_for_input = False
            line, _ = line.split("--dai")
        if "&&await_yn" in line:
            line, skip_over_yes = line.split("&&await_yn")
            self.yesno_question = int(skip_over_yes)
            if "(Y/N)" not in line:
                line += " (Y/N)"
        self.speaker_name = speaker
        line = self.engine.dialog_manager.format_text(line)
        self.current_line = line

    @evention("add_schedule")
    def add_schedule(self, line: str):
        npc, destination, time_after_now = line.split("__")
        self.engine.schedule_manager.add_dynamic_schedule_event(npc, int(time_after_now), {"target" : destination})

    @evention("remove_item")
    def remove_item(self, line: str):
        quantity = 1
        if "__" in line:
            line, quantity = line.split("__")
        self.engine.party.remove_item_by_name(line, quantity)

    @evention("talked")
    def talked(self, line: str):
        if line == "true":
            self.talked_to_npcs.add(self.engine.dialog_manager.dialog_key)
        else:
            try:
                self.talked_to_npcs.remove(self.engine.dialog_manager.dialog_key)
            except KeyError:
                pass

    @evention("forceend")
    def forceend(self):
        self.force_end = True

    @evention("give_quest")
    def give_quest(self, quest_name: str):
        self.engine.quest_log.start_quest(quest_name)
    
    @evention("give_quest_step")
    def give_quest_step(self, quest_and_quest_step: str):
        self.engine.quest_log.reveal_quest_step(quest_and_quest_step)
    
    @evention("give_quest_hint")
    def give_quest_hint(self, quest_and_quest_hint: str):
        self.engine.quest_log.reveal_quest_hint(quest_and_quest_hint)

    @evention("finish_quest")
    def finish_quest(self, quest_name: str, succeed: bool = True):
        self.engine.quest_log.finish_quest(quest_name, succeed)
    
    @evention("finish_quest_step")
    def finish_quest_step(self, quest_and_quest_step: str, succeed: bool = True):
        self.engine.quest_log.finish_quest_step(quest_and_quest_step, succeed)

    @evention("change_event_key")
    def change_event_key(self, line: str):
        obj_name, new_event = line.split("__")
        obj = self.engine.current_map.get_object_by_name(obj_name)
        try:
            obj.args["event_start"] = new_event
        except:
            raise Exception(f"{obj_name} could not be found on {self.engine.current_map.name}")
    
    @evention("walk")
    def walk(self, line: str):
        lines = line.split("&&")
        for line in lines:
            npc_name, path = line.split("__")
            if npc_name == "leader":
                npc = self.engine.party.get_leader()
            else:
                npc = self.engine.current_map.get_object_by_name(npc_name)
            if npc:
                self.walkers.append(npc)
                duration = 150
                if "--" in path:
                    path, duration = path.split("--")
                self.timer_manager.start_timer(f"event_wait_{npc.name}", int(duration))
                if not npc.last_move_direction:
                    npc.last_move_direction = (0, 0)
                self.initialize_walk(path)

    @evention("warp")
    def warp(self, line: str):
        lines = line.split("&&")
        for line in lines:
            npc_name, destination = line.split("__")
            if npc_name == "leader":
                npc = self.engine.party.get_leader()
            else:
                npc = self.engine.current_map.get_object_by_name(npc_name)
            obj = self.engine.current_map.get_object_by_name(destination)
            if npc and obj:
                npc.old_position = obj.position
                npc.position = obj.position

    @evention("spawn")
    def spawn(self, line: str):
        line_bits = line.split("__")
        if len(line_bits) >= 2:
            name = ""
            if "--" in line_bits[-1]:
                line_bits[-1], name = line_bits[-1].split("--")
            else:
                name = f"{self.event_master.name}_{line_bits[0]}_"
            if line_bits[1] == "leader":
                obj = self.engine.party.get_leader()
            else:
                obj = self.engine.current_map.get_object_by_name(line_bits[1])
            if obj:
                pos = obj.position
                new_obj = self.engine.map_obj_db.create_obj(name + "0", line_bits[0], {"x" : pos[0], "y" : pos[1]})
                print(new_obj)
                self.engine.current_map.objects.append(new_obj)
                new_obj.map = self.engine.current_map
                if len(line_bits) >= 4:
                    direction = Direction(self.engine.get_direction(line_bits[2]))
                    repeat_count = int(line_bits[3])
                    for i in range(repeat_count):
                        new_pos = obj.add_tuples(new_obj.position, direction.value)
                        new_obj = self.engine.map_obj_db.create_obj(f"{name}{i+1}", line_bits[0], {"x" : new_pos[0], "y" : new_pos[1]})
                        self.engine.current_map.objects.append(new_obj)
                        new_obj.map = self.engine.current_map

    @evention("destroy")
    def destroy(self, line: str):
        lines = line.split("&&")
        for line in lines:
            line_bits = line.split("__")
            if len(line_bits) >= 2:
                obj = self.engine.current_map.get_object_by_name(line_bits[1])
                if obj:
                    pos = obj.position
                    for old_obj in self.engine.current_map.get_objects_at(pos):
                        if old_obj.object_type == line_bits[0]:
                            self.engine.current_map.objects.remove(old_obj)
                            del old_obj
                    if len(line_bits) >= 4:
                        direction = Direction(self.engine.get_direction(line_bits[2]))
                        repeat_count = int(line_bits[3])
                        for i in range(repeat_count):
                            pos = obj.add_tuples(pos, direction.value)
                            for old_obj in self.engine.current_map.get_objects_at(pos):
                                if old_obj.object_type == line_bits[0]:
                                    self.engine.current_map.objects.remove(old_obj)
                                    del old_obj

    @evention("wait")
    def wait(self, line: str):
        self.timer_manager.start_timer("event_pause", int(line))

    @evention("invisible_leader")
    def invisible_leader(self, line: str):
        self.make_leader_invisible =  line == "true" or line == "true_nf"
        if line == "true_nf":
            return
        leader = self.engine.party.get_leader()
        if self.make_leader_invisible:
            fake_leader = self.engine.map_obj_db.create_obj("fake_leader", "mapobject", {"x" : leader.position[0], "y" : leader.position[1]})
            self.engine.current_map.add_object(fake_leader)
            fake_leader.image = leader.image
            leader.children.append(fake_leader)
        else:
            for child in leader.children:
                if child.name == "fake_leader":
                    self.engine.current_map.remove_object(child)
                    leader.children.remove(child)
                    del child
                    break

    @evention("teleport")
    def teleport(self, line: str):
        map, node = line.split("__")
        temp_tele = Teleporter.from_dict({"name" : "", "x" : -1, "y" : -1, "args" : {"target_map" : map, "position" : {"from_any" : node}}}, self.engine)
        self.engine.handle_teleporter(temp_tele, True)
        if not self.current_index >= len(self.current_event_queue["script"]):
            self.engine.change_state(GameState.EVENT)
        del temp_tele

    @evention("force_combat")
    def force_combat(self, line: str):
        if line:
            self.event_master.args["target_map"] = line
            self.event_master.args["positions"] = {"from_any" : "special_"}
        self.engine.handle_teleporter(self.event_master, True)
        self.engine.combat_manager.enter_combat_mode()
        for obj in self.engine.current_map.objects:
            if obj.name == "event_at_combat_start":
                self.engine.change_state(GameState.EVENT)
                break

    def _check_condition(self, condition: str):
        if not condition:
            return True
        true_if = not condition[0] == "!"
        if not true_if:
            condition = condition[1:]
        if "=" not in condition:#Then this is a flag
            return (condition in self.flags) == true_if
        condition, line = condition.split("=")
        match condition:
            case "last_dialog":
                return ch.last_dialog(self.engine.dialog_manager.last_input, line, true_if)
            case "talked":
                return ch.talked(self.engine.dialog_manager.dialog_key, self.talked_to_npcs, true_if)
            case "have_item":
                return ch.have_item(self.engine.party, line, true_if)
            case "have_quest":
                return ch.have_quest(self.engine.quest_log.quests.get(line, None), true_if)
            case "mid_quest":
                return ch.mid_quest(self.engine.quest_log.quests.get(line, None), true_if)
            case "finished_quest":
                return ch.finished_quest(self.engine.quest_log.quests.get(line, None), true_if)
            case "have_quest_step":
                line, quest_step_name = line.split("__")
                return ch.have_quest_step(self.engine.quest_log.quests.get(line, None), quest_step_name, true_if)
            case "finished_quest_step":
                line, quest_step_name = line.split("__")
                return ch.finished_quest_step(self.engine.quest_log.quests.get(line, None), quest_step_name, true_if)
            case "leader_wear":
                leader = self.engine.party.get_leader()
                return ch.leader_wear(leader, line, true_if)
            case "leader_direction":
                leader = self.engine.party.get_leader()
                if self.engine.state == GameState.DIALOG:
                    reference = self.engine.dialog_manager.current_speaker
                else:
                    reference = self.event_master
                direction = self.engine.get_direction(line)
                return ch.leader_direction(leader, reference, direction, true_if)
        if condition[0] == "!":
            return condition[1:] not in self.flags
        return condition in self.flags

        

    def _do_event(self, line: str):
        event, line = line.split("=")
        match event:
            case "reset_map":
                for obj in self.engine.current_map.objects:
                    obj.old_position = obj.init_position
                    obj.position = obj.init_position
            case "set_flag":
                self.set_flag(line)
            case "del_flag":
                self.del_flag(line)
            case "clear_flag":
                self.flags = set()
            case "add_item":
                self.add_item(line)
            case "jump":
                self.jump(int(line))
            case "add_schedule":
                self.add_schedule(line)
            case "give_gold":
                self.give_gold(int(line))
            case "remove_item":
                self.remove_item(line)
            case "cutscene":
                self.start_cutscene()
            case "talked":
                self.talked(line)
            case "force_end":
                self.forceend()
            case "delayed_event_start":
                if line in self.events:
                    self.delayed_events["event_start"] = line
            case "delayed_teleport":
                self.delayed_teleport(int(line))
            case "give_quest":
                self.give_quest(line)
            case "give_quest_step":
                self.give_quest_step(line)
            case "give_quest_hint":
                self.give_quest_hint(line)
            case "finish_quest":
                quest_name, succeed = line.split("--")
                self.finish_quest(quest_name, succeed == "true")
            case "finish_quest_step":
                quest_step, succeed = line.split("--")
                self.finish_quest_step(quest_step, succeed == "true")
            case "text":
                self.text(line)     
            case "walk":
                self.walk(line)
            case "warp":
                self.warp(line)
            case "change_event_key":
                self.change_event_key(line)
            case "force_combat":
                self.force_combat(line)
            case "reforce_combat":
                self.engine.combat_manager.enter_combat_mode()
            case "spawn":
                self.spawn(line)
            case "destroy":
                self.destroy(line)
            case "wait":
                self.wait(line)
            case "invisible_leader":
                self.invisible_leader(line)
            case "teleport":
                self.teleport(line)
    
    def to_dict(self):
        return {
            "flags" : list(self.flags),
            "talked_to_npcs" : list(self.talked_to_npcs)
        }
    
    @classmethod
    def from_dict(cls, data, engine):
        data["engine"] = engine
        data["flags"] = set(data["flags"])
        data["talked_to_npcs"] = set(data["talked_to_npcs"])
        return cls(**data)

                

    
