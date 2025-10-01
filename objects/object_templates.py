import os, pygame
from dataclasses import dataclass, asdict, fields, MISSING, field
from random import randint
from typing import List, Dict, Any, Optional, Type, TYPE_CHECKING, Literal
from constants import *
from items.itemz import Item
from schedules.schedule import ScheduleEvent, datetime
if TYPE_CHECKING:
    from objects.characters import Character
    from ultimalike import GameEngine
    from objects.map_objects import Map
    from objects.nodegroup import NodeGroup
NODE_REGISTRY: Dict[str, Type['Node']] = {}

def register_node_type(name: str):
    def decorator(cls):
        NODE_REGISTRY[name] = cls
        return cls
    return decorator
@register_node_type("node")
@dataclass
class Node:
    name: str
    args: dict[str, Any] = field(default_factory=lambda: {})
    layer: int = 1
    width_in_tiles = 1
    height_in_tiles = 1
    can_bump: bool = True
    is_bumping: bool = False
    bump_direction: Direction = None
    init_position: tuple[int, int] = (0, 0)
    old_position: tuple[int, int]= (0, 0)
    position: tuple[int, int]= (0, 0)
    skin_color: tuple[int, int, int] = (0, 0, 0)
    state: ObjectState = ObjectState.STAND
    after_state: ObjectState = ObjectState.STAND
    parent: 'Node' = None
    children: list['Node'] = field(default_factory=lambda: [])
    group_name: str = ""
    group: 'NodeGroup' = None
    pronoun: str = "it"
    prepositional: str = "it"
    possessive: str = "its"

    engine: 'GameEngine' = None
    object_type: str = None
    activate_by_stepping_on = True
    color = RED
    image = None
    fixed_spritesheet_row: int = 0
    node_id = 0
    map: 'Map' = None
    is_passable: bool = True
    can_see_thru = True
    destroy_after_use: bool = False
    def __is__(self, cls):
        return isinstance(self, cls)
    def to_dict(self):
        return {"object_type" : self.object_type, "args" : self.args, "position" : self.position, "old_position" : self.old_position, "skin_color" : self.skin_color, "group_name" : self.group_name}
    @staticmethod
    def from_dict(data: dict, engine: 'GameEngine') -> 'Node':
        node_type = data.get("object_type")
        cls = NODE_REGISTRY.get(node_type, Node)
        base_args = cls.default_args()
        user_args = data.get("args", {})
        merged_args = {**base_args, **user_args}
        data["args"] = merged_args
        new_node = cls(**data)
        new_node.engine = engine
        try:
            if "spritesheet" in new_node.args:
                if new_node.args["spritesheet"][0].startswith("Generic People"):
                    if "skin_color" in data:
                        if type(data["skin_color"]) == list:
                            new_node.skin_color = tuple(data["skin_color"])
                        else:
                            new_node.skin_color = new_node.engine.sprite_db.common_skin_colors[int(data["skin_color"])]
                    else:
                        new_node.skin_color = new_node.engine.sprite_db.common_skin_colors[randint(0, len(new_node.engine.sprite_db.common_skin_colors) - 1)]
            new_node.engine.sprite_db.get_sprite(new_node)
        except:
            print(f"Could not load sprite for {new_node.name}")
        gendered_key = new_node.args.get("gendered_words", "")
        if gendered_key:
            gendered_words = GENDEREDWORDS[gendered_key]
            new_node.pronoun = gendered_words[0]
            new_node.prepositional = gendered_words[1]
            new_node.possessive = gendered_words[2]
        new_node.position = tuple(new_node.position)
        new_node.init_position = new_node.position
        new_node.old_position = new_node.position
        
        return new_node
    
    def interact(self) -> bool:
        return False
    
    def get_objects_in_adjacent_tiles(self):
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for obj in self.map.get_objects_at(self.add_tuples(self.position, (i, j))):
                    yield obj

    @staticmethod
    def default_args() -> dict:
        return {}
    
    @staticmethod
    def get_sign(num: tuple | int | float) -> tuple | Literal[-1] | Literal[1] | Literal[0]:
        """
        Determines if a number (or tuple of numbers) is positive, negative, or neither.
        """
        if type(num) == tuple:
            return tuple(Node.get_sign(n) for n in num)
        else:
            return -1 if num < 0 else (1 if num > 0 else 0)
    @staticmethod
    def add_tuples(tuple1: tuple, tuple2: tuple | int | float) -> tuple:
        """
        Adds two tuples together, or adds the number tuple2 to each element of tuple1
        """
        if type(tuple2) in [int, float]:
            b = tuple2
            return tuple(a + b for a in tuple1)
        if len(tuple1) != len(tuple2):
            raise ValueError
        return tuple(a + b for a, b in zip(tuple1, tuple2))
    
    @staticmethod
    def subtract_tuples(tuple1: tuple, tuple2: tuple | int | float) -> tuple:
        """
        Subtracts two tuples, or subtracts the number tuple2 from each element of tuple1
        """
        if type(tuple2) in [int, float]:
            b = tuple2
            return tuple(a - b for a in tuple1)
        if len(tuple1) != len(tuple2):
            raise ValueError
        return tuple(a - b for a, b in zip(tuple1, tuple2))
    
    @staticmethod
    def multiply_tuples(tuple1: tuple, tuple2: tuple | int | float) -> tuple:
        if type(tuple2) in [int, float]:
            b = tuple2
            return tuple(a * b for a in tuple1)
        if len(tuple1) != len(tuple2):
            raise ValueError
        return tuple(a * b for a, b in zip(tuple1, tuple2))
    
    def distance(self, obj: 'Node', can_move_diagonally: bool = True) -> tuple[int, tuple[int, int]]:
        diff = self.subtract_tuples(obj.position, self.position)
        if can_move_diagonally:
            return max(abs(diff[0]), abs(diff[1])), diff
        return abs(diff[0]) + abs(diff[1]), diff
    
    def update(self, **args):
        pass

    def draw(self):
        pass

    def on_map_load(self):
        if "on_load_event" in self.args:
            self.engine.event_manager.start_event(self.args["on_load_event"], self, treat_as_event=False)

    def destroy(self):
        if self.parent:
            self.parent.children.remove(self)
        if self.map:
            self.map.remove_object(self)
        if self in self.engine.combat_manager.enemy_turn_queue:
            self.engine.combat_manager.enemy_turn_queue.remove(self)
        del self
        

@register_node_type("mapobject")
@dataclass
class MapObject(Node):
    move_interval: float = 0.0
    can_be_attacked = False
    current_target: Node = None
    current_event: ScheduleEvent = None
    next_move_time: datetime = None
    patrol_node_template: str = ""
    max_node: int = -1
    node_id = 1
    look_text: str = None
    is_hostile = False
    is_passable: bool = False
    last_move_direction: tuple[int, int] = None
    allies_in_combat: List[str] = None
    ally_positions: str = None  # Added to dataclass fields
    
    # Track movement progress for the current action
    current_action_start_turn = 0
    moves_completed_this_action = 0

    def to_dict(self):
        my_dict = super().to_dict()
        my_dict["move_interval"] = self.move_interval
        my_dict["state"] = self.state.value
        if self.look_text:
            my_dict["look_text"] = self.look_text
        return my_dict

    @staticmethod
    def from_dict(data: dict, engine: 'GameEngine') -> 'MapObject':
        new_obj = super(MapObject, MapObject).from_dict(data, engine)
        new_obj.move_interval = data.get("move_interval", 0.0)
        new_obj.state = ObjectState(data.get("state", ObjectState.STAND.value))
        return new_obj

    def update_from_schedule(self):
        """
        Update NPC state based on current schedule. Call this when loading a map
        or when you want to sync NPC with their schedule.
        """
        status = self.engine.schedule_manager.get_npc_schedule_status(self.name, self.move_interval)
        
        if not status['current_event']:
            self.state = ObjectState.STAND
            self.current_target = None
            self.current_event = None
            return
        
        event = status['current_event']
        movement_turns = status['movement_turns']
        
        # Check if this is a NEW event (different from what we're currently doing)
        is_new_event = (self.current_event is None or 
                       self.current_event.time_minutes != event.time_minutes)
        
        if is_new_event:
            # This is a new event, execute it and reset movement tracking
            self.execute_action(event)
            self.current_event = event
            self.moves_completed_this_action = 0
        
        # Fast-forward movement to catch up to where NPC should be
        # (but don't reset patrol progress unless it's a new event)
        if movement_turns > self.moves_completed_this_action:
            self.catch_up_movement(movement_turns)
    
    def catch_up_movement(self, target_moves: float):
        """
        Move the NPC the specified number of steps toward their target
        to catch up with where they should be based on elapsed time.
        """
        moves_needed = int(target_moves - self.moves_completed_this_action)
        
        for _ in range(moves_needed):
            if self.state in [ObjectState.WALK, ObjectState.PATROL] and self.current_target:
                self.move_one_step_immediate()
            else:
                break
        
        self.moves_completed_this_action = target_moves

    def move_one_step_immediate(self, done_walking: bool = True):
        """
        Move one step immediately without time checks.
        Used for catching up to scheduled position.
        """
        if self.state in [ObjectState.WALK, ObjectState.PATROL] and self.current_target:
            me = self.position
            my_target = self.current_target.position
            self.last_move_direction = Direction(self.get_sign(self.subtract_tuples(my_target, me)))
            self.old_position = me
            
            if self.group:
                if not self.group.checked_movement: #No point going through this for every node
                    can_move = True
                    for obj in self.group.nodes:
                        if obj.is_passable: #Don't bother with calculations if this can pass through anything.
                            continue
                        new_position = self.add_tuples(obj.position, self.last_move_direction.value)
                        if not self.map.is_passable(new_position):
                            can_move = False#Even one failure means no moving
                            break
                    if can_move:
                        for obj in self.group.nodes:
                            obj.old_position = obj.position
                            obj.last_move_direction = self.last_move_direction
                            obj.position = self.add_tuples(obj.position, self.last_move_direction.value)
                    self.group.checked_movement = True
            else:
                new_position = self.add_tuples(me, self.last_move_direction.value)
                if self.is_passable or self.map.is_passable(new_position):
                    self.position = new_position
            
            # Check if we reached our target
            if self.position == my_target:
                if self.state == ObjectState.WALK:
                    self.current_target = None
                    self.state = ObjectState.STAND
                elif self.state == ObjectState.PATROL:
                    self.next_node()

    def move_one_step(self):
        """
        Updated version that works with turn-based schedule manager.
        Call this during normal gameplay when a turn advances.
        """
        # Check if enough time has passed for this NPC to move
        status = self.engine.schedule_manager.get_npc_schedule_status(self.name, self.move_interval)
        
        if not status['current_event']:
            return

        # Handle repeating actions (like firing arrows)
        if status['should_repeat']:
            event = status['current_event']
            event.repeat_count_current += 1
            self.execute_repeating_action(event)
        
        # Handle movement for movement-based actions
        if status['current_event'].action in ["go_to", "patrol"]:
            expected_moves = status['movement_turns']
            
            while expected_moves > self.moves_completed_this_action:
                # We should move this turn
                self.move_one_step_immediate()
                self.moves_completed_this_action += 1

    
    def execute_action(self, action: ScheduleEvent):
        """Execute a scheduled action - updated for new schedule manager."""
        if action.action == "go_to" and action.target:
            self.go_to(action.target)
            
        elif action.action == "patrol":
            self.start_patrol(action)

        
        # Reset movement tracking for new action
        self.moves_completed_this_action = 0

    def execute_repeating_action(self, action: ScheduleEvent):
        #This function is a placeholder, to be re-defined based on the subclass of the object performing the repeating action
        pass
    
    def go_to(self, target: str):
        """Execute go_to action."""
        self.current_target = self.map.get_object_by_name(target)
        if self.current_target:
            print(f"My target, {self.current_target.name}, does exist. I will walk at them at an interval of {self.move_interval}")
            self.state = ObjectState.WALK
            return self.current_target
        return None

    def next_node(self):
        next_num = int(self.current_target.name.split("_")[-1]) + 1
        if next_num >= self.max_node:
            next_num = 0
        self.current_target = self.map.get_object_by_name(f"{self.patrol_node_template}_{str(next_num)}")

    def start_patrol(self, action: ScheduleEvent):
        self.patrol_node_template = action.patrol_node_template
        self.current_target = self.map.get_object_by_name(f"{self.patrol_node_template}_{action.start_node}")
        if self.current_target:
            self.max_node = action.max_node
            self.state = ObjectState.PATROL
        

@register_node_type("chest")
class Chest(MapObject):
    color = DARK_GRAY
    node_id = 2
    def interact(self):
        if "spritesheet" in self.args and "no_open_sprite" not in self.args:
            self.engine.sprite_db.get_sprite(self, new_col=1 - self.args["spritesheet"][2])
        items = self.args.get("items", {})
        for item_name, quantity in items.items():
            item = self.engine.party.add_item_by_id(item_name, quantity)
            if quantity > 1:
                message = f"You got {item.plural} x{quantity}"
            else:
                article = ""
                if not item.omit_article:
                    article = "the " if "special" in item_name else ("an " if any([item_name.startswith(vowel) for vowel in 'aeiou']) else "a ")
                message = f"You got {article}{item.name}!"
            self.engine.append_to_message_log(message)
            if item.name == "Burnt Book Cover":
                message = "(You can show items to people in dialog by typing #show#, then selecting the item.)"
                self.engine.append_to_message_log(message)
                message = "(Try it with the coroner to the south.)"
                self.engine.append_to_message_log(message)
        self.args["items"] = {}
        return True

@register_node_type("itemholder")
class ItemHolder(MapObject):
    is_passable = True
    node_id = 7

@register_node_type("npc")
@dataclass
class NPC(MapObject):
    can_be_attacked = True
    color = BLACK
    node_id = 3

@register_node_type("teleporter")
class Teleporter(Node):
    color = MAGENTA
    node_id = 4
    

class CombatStatsMixin:
    hp: int = 5
    max_hp: int = 5
    base_max_hp: int = 5
    min_max_hp: int = 1
    max_hp_delta: int = 0
    power: int = 0
    power_delta: int = 0
    power_mult: float = 1.0
    guard: int = 0
    guard_delta: int = 0
    guard_mult: float = 1.0
    engine: 'GameEngine' = None
    pos: tuple[int, int] = (0, 0)
    map: 'Map' = None
    name: str = ""
    can_move_diagonally: bool = True
    equipped: Dict[str, Optional[Item]] = None  # New field
    strength: int = 0
    min_strength: int = 0
    strength_delta: int = 0
    strength_mult: float = 1.0
    dexterity: int = 0
    min_dexterity: int = 0
    dexterity_delta: int = 0
    dexterity_mult: float = 1.0
    faith: int = 0
    min_faith: int = 0
    faith_delta: int = 0
    faith_mult: float = 1.0
    body_status_in: InternalBodyStatus = None
    body_status_in_counter: int = 0
    body_status_ex: ExternalBodyStatus = None
    body_status_ex_counter: int = 0
    mind_status: MindStatus = None
    mind_status_counter: int = 0
    parasite_in: 'CombatStatsMixin' = None
    parasite_ex: 'CombatStatsMixin' = None
    dies_if_host_on_fire: bool = True

    def get_total_power(self):
        return int(self.power_mult*(self.get_strength() + self.power + self.power_delta))
    
    def get_total_guard(self):
        return int(self.guard_mult*(self.get_dexterity() + self.guard + self.guard_delta))
    
    def get_max_hp(self):
        return max(self.max_hp + self.max_hp_delta, self.min_max_hp)
    
    def get_strength(self):
        return max(self.strength + self.strength_delta, self.min_strength)
    
    def get_dexterity(self):
        return max(self.dexterity + self.dexterity_delta, self.min_dexterity)
    
    def get_faith(self):
        return max(self.faith + self.faith_delta, self.min_faith)
    
    def get_closest_obj(self, obj_list: List = None):
        closest_obj = None
        min_dist = 999999
        if not obj_list:
            obj_list = self.map.objects
        for obj in obj_list:
            if obj == self:
                continue
            if not hasattr(obj, 'hp') or not hasattr(obj, 'experience'):
                continue
            dist = obj.distance(self, self.can_move_diagonally)
            if not closest_obj:
                closest_obj = obj
                min_dist = dist
            elif dist < min_dist:
                closest_obj = obj
                min_dist = dist
            elif dist == min_dist and obj.hp < closest_obj.hp:
                closest_obj = obj
        return closest_obj
                
    def restore_hp(self, amount: int) -> int:
        max_hp = self.get_max_hp()
        if max_hp < self.hp + amount:
            amount_restored = max_hp - self.hp
            self.hp = max_hp
        else:
            amount_restored = amount
            self.hp += amount
        return amount_restored
    
    def attack(self, target: 'CombatStatsMixin', damage: int = 0):
        if not damage:
            damage = max(1, self.get_total_power() - target.get_total_guard())
        target.hp -= damage
        target.attacked(self, damage)
        if target.hp <= 0 and target == self.current_target:
            self.current_target = None
        return damage

    def attacked(self, attacker, damage: int = 0):
        if self.hp <= 0:
            self.death()


    def death(self):
        self.state = ObjectState.DYING
    
    def my_battle_tactics(self):
        if self.hp <= 0:
            return

    
@register_node_type("monster")
@dataclass
class Monster(CombatStatsMixin, Node):
    image = None
    color = LIGHT_BLUE
    can_be_pushed = True
    flying = False  # If True, this monster cannot be knocked back
    can_be_attacked = True
    node_id = 6
    is_vengeful: bool = True
    is_honorable: bool = False
    is_breakable: bool = False
    is_passable: bool = False
    is_hostile: bool = True
    move_tiles_per_turn: int = 1
    current_target: 'Character' = None
    def update(self, **args):
        super().update(**args)
        match self.state:
            case ObjectState.KNOCKBACK:
                if self.engine.event_manager.timer_manager.get_progress(f"{self.name}_knockback") >= 1.0:
                    self.old_position = self.position
                    self.state = self.after_state
            case ObjectState.COLLISION_KNOCKBACK:
                self.hp -= 5
                self.state = ObjectState.STAND if self.hp > 0 else ObjectState.DYING
            case ObjectState.COLLISION_STAND:
                self.hp -=50
                self.state = ObjectState.STAND if self.hp > 0 else ObjectState.DYING
            case ObjectState.DYING:
                self.is_passable = True
                self.engine.sprite_db.get_sprite(self, 0, 0)
                self.state = ObjectState.DEATH
            case ObjectState.DEATH:
                pass
    
    @classmethod
    def from_dict(cls, data, engine: 'GameEngine'):
        cls = super().from_dict(data, engine)
        cls.hp = cls.max_hp
        return cls


    def push(self, attacker: CombatStatsMixin, direction: Direction, count: int = 1):
        """
        Push this object back in the specified direction.
        Used for knockback effects.
        Return the duration of the knockback effect.
        """
        tiles_back = 0
        if self.can_be_pushed and not self.flying:
            self.old_position = self.position
            for i in range(count):
                new_position = self.add_tuples(self.position, direction.value)
                if not self.map.is_passable(new_position):
                    self.after_state = ObjectState.COLLISION_KNOCKBACK
                    break  # Stop if we hit a wall or another unit
                self.position = new_position
                tiles_back += 1
            
            if tiles_back:
                self.state = ObjectState.KNOCKBACK
                self.engine.event_manager.timer_manager.start_timer(f"{self.name}_knockback", tiles_back*150)
                self.engine.combat_manager.walkers.append(self)
                self.engine.combat_manager.append_to_combat_log(f"{attacker.name} sent {self.name} flying back {tiles_back} spaces!")
            else:
                self.engine.combat_manager.append_to_combat_log(f"{attacker.name} failed to send {self.name} flying!")


@register_node_type("missile")
@dataclass
class Missile(MapObject):
    leftover: int = 0
    damage: int = 5
    hits_player: bool = False
    move_direction: Direction = Direction.EAST
    def move_one_step(self):
        if self.move_interval <= 0:
            return
        self.moves_completed_this_action = 0
        expected_moves = (self.engine.schedule_manager.turn_history[-1] + self.leftover)//self.move_interval
        self.leftover = self.engine.schedule_manager.turn_history[-1] - expected_moves*self.move_interval
        my_direction = self.move_direction
        me = self.position
        self.old_position = me
        while expected_moves > self.moves_completed_this_action:
            # We should move this turn
            new_pos = self.add_tuples(self.position, my_direction.value)
            if not self.map.is_passable(new_pos):
                if self.engine.party.get_leader().position == new_pos:
                    self.hits_player = True
                self.destroy_after_use = True
                self.moves_completed_this_action = expected_moves - 1
            self.position = new_pos
            self.moves_completed_this_action += 1
    def destroy(self):
        if self.hits_player:
            self.engine.party.get_leader().hp -= self.damage
        super().destroy()
            


class Spawner:
    def spawn_object_at_position(self, obj_type: str, obj_name: str = "", position: tuple[int, int] = None):
        if not obj_name:
            obj_name = self.name + "_" + obj_type + "_" + str(0 if not self.children else len(self.children))
        if not position:
            position = self.position
        obj = self.engine.map_obj_db.create_obj(obj_name, obj_type, {"position" : position})
        if obj:
            obj.parent = self
            self.children.append(obj)
            self.map.add_object(self.children[-1])
        return obj