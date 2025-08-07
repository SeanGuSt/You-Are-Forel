import pygame
import os
import json
from constants import EVENT_DIR, GameState, Direction
from typing import TYPE_CHECKING
from objects.map_objects import Node, Map, MapObject, Teleporter
from dialog.dialog_helpers import format_time_of_day
import re
if TYPE_CHECKING:
    from ultimalike import GameEngine
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
        self.flags = flags #Track various dialog flags. Needs to be saved
        self.talked_to_npcs = talked_to_npcs
        self.pending_events = {}
        self.delayed_events = {}
        self.timers = {
            "player_move" : 0,
            "event_wait" : 0,
            "teleporter_delay" : 0,
            "event_pause" : 0,
            "enemy_move" : 0,
            "player_bump" : 0
        }
        self.timer_limits = {
            "player_move" : 0,
            "event_wait" : 0,
            "enemy_move" : 0,
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
                    dialogs = json.load(f)
                    if dialogs:
                        for key, value in dialogs.items():
                            self.events[key] = value
                            

    def start_event(self, key: str, event_master: Node, force_start: bool = False):
        if key in self.events:
            my_queue = self.events[key]
            conditions = my_queue.get("conditions", [])
            conditions_met = all(self._check_condition(condition) for condition in conditions)
            if conditions_met:
                self.event_master = event_master
                if force_start:
                    my_queue["trigger"] = "on_step"
                match my_queue["trigger"]:
                    case "on_step":
                        self.current_event_queue = my_queue
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
        

    def advance_queue(self):
        if not self.current_event_queue or self.waiting_for_input or self.walkers:
            return
        if self.timers["event_pause"] < self.event_pause_timer:
            self.timers["event_pause"] += 1
            return
        else:
            self.timers["event_pause"] = 0
            self.event_pause_timer = 0
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
            

    def end_event(self):
        self.current_index = -1
        self.engine.revert_state()
        destroy_trigger_node = self.current_event_queue.get("destroy_trigger_object", "")
        em = self.event_master
        if destroy_trigger_node == "after_trigger" and em:
           self.engine.current_map.remove_object(em)
           del em
        for tl in self.timer_limits:
            self.timer_limits[tl] = 0
        self.current_event_queue = {}
        self.event_master = None
        self.waiting_for_input = False

    
    def give_gold(self, gold: int):
        self.engine.party.gold += gold
        return True
    
    def delayed_teleport(self, delay_time: int):
        teleporter_here = self.engine.current_map.get_object_by_name(self.pending_events["new_args"]["position"]["from_any"])
        print(self.pending_events["new_args"]["position"]["from_any"])
        print(teleporter_here)
        teleporter_here.args = self.pending_events["new_args"]
        self.pending_events = {}
        self.delayed_events = {
            "teleporter" : teleporter_here,
            "delay" : delay_time*self.engine.FPS/1000
        }
    
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
        if self.walkers and self.timers["event_wait"] >= self.timer_limits["event_wait"]:
            self.timers["event_wait"] = 0
            if not self.walk_directions:
                self.walkers = []
                self.timer_limits["event_wait"] = 0
                return
            for i, obj in enumerate(self.walkers):
                if not self.walk_directions[i]:
                    self.walkers.remove(obj)
                    self.walk_directions.remove(self.walk_directions[i])
                    continue
                direc = self.engine.get_direction(self.walk_directions[i][0])
                tpos = obj.add_tuples(obj.position, direc.value)
                self.walk_directions[i] = self.walk_directions[i][1:]
                if obj.map.is_passable(tpos) or ignore_walls:
                    obj.old_position = obj.position
                    obj.position = tpos
                    obj.last_move_direction = direc.value
        else:
            self.timers["event_wait"] += 1

    def give_quest(self, quest_name: str):
        self.engine.quest_log.start_quest(quest_name)
    
    def give_quest_step(self, quest_and_quest_step: str):
        self.engine.quest_log.reveal_quest_step(quest_and_quest_step)
        
    def give_quest_hint(self, quest_and_quest_hint: str):
        self.engine.quest_log.reveal_quest_hint(quest_and_quest_hint)

    def finish_quest(self, quest_name: str, succeed: bool = True):
        self.engine.quest_log.finish_quest(quest_name, succeed)
    
    def finish_quest_step(self, quest_and_quest_step: str, succeed: bool = True):
        self.engine.quest_log.finish_quest_step(quest_and_quest_step, succeed)

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
                return (self.engine.dialog_manager.last_input in line.split("|")) == true_if
            case "talked":
                return (self.engine.dialog_manager.dialog_key in self.talked_to_npcs) == true_if
            case "have_quest":
                quest = self.engine.quest_log.quests.get(line, None)
                if quest:
                    return quest.started == true_if
                else:
                    return False == true_if
            case "leader_wear":
                leader = self.engine.party.get_leader()
                if leader:
                    for item in leader.equipped.values():
                        if item:
                            if item.item_id in line.split("|"):
                                return true_if
                    return not true_if
        if condition[0] == "!":
            return condition[1:] not in self.flags
        return condition in self.flags

        

    def _do_event(self, line: str):
        event, line = line.split("=")
        match event:
            case "add_item":
                quantity = 1
                if "__" in line:
                    line, quantity = line.split("__")
                self.engine.party.add_item_by_name(line, quantity)
            case "add_schedule":
                npc, destination, time_after_now = line.split("__")
                self.engine.schedule_manager.add_dynamic_schedule_event(npc, int(time_after_now), {"target" : destination})
            case "give_gold":
                self.give_gold(int(line))
            case "remove_item":
                quantity = 1
                if "__" in line:
                    line, quantity = line.split("__")
                self.engine.party.remove_item_by_name(line, quantity)
            case "cutscene":
                self.engine.cutscene_manager.start_scene(line)
            case "talked":
                if line == "true":
                    self.talked_to_npcs.add(self.engine.dialog_manager.dialog_key)
                else:
                    try:
                        self.talked_to_npcs.remove(self.engine.dialog_manager.dialog_key)
                    except KeyError:
                        pass
            case "force_end":
                self.force_end = True
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
            case "text":
                speaker, line = line.split("__")
                if "&&await_yn" in line:
                    line, skip_over_yes = line.split("&&await_yn")
                    self.yesno_question = int(skip_over_yes)
                    if "(Y/N)" not in line:
                        line += " (Y/N)"
                self.speaker_name = speaker
                if "{time_of_day}" in line:
                    line = format_time_of_day(line, self.engine.schedule_manager.current_game_time)
                self.current_line = line
                self.waiting_for_input = True
            case "walk":
                lines = line.split("&&")
                for line in lines:
                    npc_name, path = line.split("__")
                    if npc_name == "leader":
                        npc = self.engine.party.get_leader()
                    else:
                        npc = self.engine.current_map.get_object_by_name(npc_name)
                    if npc:
                        self.walkers.append(npc)
                        if not npc.last_move_direction:
                            npc.last_move_direction = (0, 0)
                        self.initialize_walk(path)
                if self.walkers:
                    self.timers["event_wait"] = 8
                    self.timer_limits["event_wait"] = 8
                    self.continue_walk()
            case "force_combat":
                if line:
                    self.event_master.args["target_map"] = line
                    self.event_master.args["positions"] = {"from_any" : "special"}
                self.engine.handle_teleporter(self.event_master, True)
                self.engine.combat_manager.enter_combat_mode()
            case "spawn":
                line_bits = line.split("__")
                if len(line_bits) >= 2:
                    obj = self.engine.current_map.get_object_by_name(line_bits[1])
                    if obj:
                        pos = obj.position
                        new_obj = self.engine.map_obj_db.create_obj(f"{self.event_master.name}_{line_bits[0]}_0", line_bits[0], {"x" : pos[0], "y" : pos[1]})
                        self.engine.current_map.objects.append(new_obj)
                        new_obj.map = self.engine.current_map
                        if len(line_bits) >= 4:
                            direction = Direction(self.engine.get_direction(line_bits[2]))
                            repeat_count = int(line_bits[3])
                            for i in range(repeat_count):
                                new_pos = obj.add_tuples(new_obj.position, direction.value)
                                new_obj = self.engine.map_obj_db.create_obj(f"{self.event_master.name}_{line_bits[0]}_{i+1}", line_bits[0], {"x" : new_pos[0], "y" : new_pos[1]})
                                self.engine.current_map.objects.append(new_obj)
                                new_obj.map = self.engine.current_map
            case "destroy":
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
            case "wait":
                self.event_pause_timer = int(line)*self.engine.FPS/1000
            case "invisible_leader":
                self.make_leader_invisible =  line == "true"
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

            case "teleport":
                map, node = line.split("__")
                temp_tele = Teleporter.from_dict({"name" : "", "x" : -1, "y" : -1, "args" : {"target_map" : map, "position" : {"from_any" : node}}}, self.engine)
                self.engine.handle_teleporter(temp_tele, True)
                if not self.current_index >= len(self.current_event_queue["script"]):
                    self.engine.change_state(GameState.EVENT)
                del temp_tele
    
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

                

    
