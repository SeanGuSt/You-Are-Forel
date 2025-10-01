from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Any, Optional, TYPE_CHECKING
from items.itemz import Item, ItemEffect, ItemDatabase, Equipment
from constants import *
import copy, ast
from magic.virtue import VirtueManager, VirtueType
import pygame
from objects.object_templates import Node, MapObject, CombatStatsMixin
if TYPE_CHECKING:
    from objects.map_objects import Map
    from magic.magic import Spell
    from ultimalike import GameEngine

# Modified Character Class
@dataclass
class Character(CombatStatsMixin, Node):
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    mp: int = 50#Ignore
    max_mp: int = 50#Ignore
    strength: int = 1
    dexterity: int = 1
    faith: int = 1
    experience: int = 0
    last_move_direction: tuple[int, int] = (0, 0)

    special: bool = False
    is_passable: bool = False
    prepped_spell: 'Spell' = None
    frames_since_last_change: int = 0
    
    engine: 'GameEngine' = None
    virtue_used_this_turn: VirtueType = None
    virtue_manager: VirtueManager = VirtueManager()#This is where the spell classes' overuse points should be stored, and their penalties handled
    
    def __post_init__(self):
        if self.equipped is None:
            self.equipped = {slot.value: None for slot in EquipmentSlot}
    
    def equip_item(self, equipment: Equipment) -> Optional[Equipment]:
        """Equip an item, returning the previously equipped item if any"""
        slot_key = equipment.slot.value
        previously_equipped = self.equipped.get(slot_key)
        if slot_key == "armor" and equipment.item_id != "armor_pjs" and "wore_real_clothes" not in self.engine.event_manager.flags:
            self.engine.event_manager.flags.add("wore_real_clothes")
            self.engine.quest_log.finish_quest_step("assure_eraton__get_dressed")
        
        # Unequip previous item
        if previously_equipped:
            print("Started Unequipping")
            print(self.args["spritesheet"])
            self.apply_equipment_effects(previously_equipped, unequip=True)
            print("Finished Unequipping")
            print(self.args["spritesheet"])
        
        # Equip new item
        self.equipped[slot_key] = equipment
        self.apply_equipment_effects(equipment, unequip=False)
        
        return previously_equipped
    
    def unequip_item(self, slot: EquipmentSlot) -> Optional[Item]:
        """Unequip an item from the specified slot"""
        slot_key = slot.value
        equipment = self.equipped.get(slot_key)
        
        if equipment:
            self.apply_equipment_effects(equipment, unequip=True)
            self.equipped[slot_key] = None
        
        return equipment
    
    def apply_equipment_effects(self, equipment: Item, unequip: bool = False):
        """Apply or remove equipment effects"""
        multiplier = -1 if unequip else 1
        
        for etype, etrigger, estat, evalue in zip(equipment.effects, equipment.triggers, equipment.estats, equipment.evalues):
            if etrigger == EffectTrigger.PASSIVE:
                if etype == EffectType.STAT_BUFF:
                    if estat == "strength":
                        self.strength_delta += evalue * multiplier
                    elif estat == "dexterity":
                        self.dexterity_delta += evalue * multiplier
                    elif estat == "faith":
                        self.faith_delta += evalue * multiplier
                    elif estat == "max_hp":
                        self.max_hp_delta += evalue * multiplier
                        self.hp = max(min(self.hp + evalue * multiplier, self.max_hp), 1)
                    elif estat == "max_mp":
                        self.max_mp += evalue * multiplier
                        self.mp += evalue * multiplier
                elif etype == EffectType.CHANGE_SPRITE:
                    is_delta = False
                    if estat == "0":
                        self.fixed_spritesheet_row = 0 if unequip else evalue
                        if not self.fixed_spritesheet_row:
                            evalue = self.args["spritesheet"][1]
                        else:
                            evalue = None
                    elif (not unequip and estat == "+") or (unequip and estat == "-"):
                        is_delta = True
                    elif (not unequip and estat == "-") or (unequip and estat == "+"):
                        is_delta = True
                        evalue = -evalue
                    self.engine.sprite_db.get_sprite(self, new_row = evalue, is_delta = is_delta)

    def update(self, **args):
        super().update(**args)
        timer_manager = self.engine.event_manager.timer_manager
        match self.state:
            case ObjectState.STAND:
                if self.body_status_ex == ExternalBodyStatus.ON_FIRE:
                    self.state = ObjectState.BURNING
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = 0)
            case ObjectState.TALK:
                self.engine.sprite_db.get_sprite(self, new_col = 3)
            case ObjectState.BURNING:
                if self.body_status_ex != ExternalBodyStatus.ON_FIRE:
                    if self.hp > 0:
                        self.state = ObjectState.STAND
                    else:
                        self.state = ObjectState.DEATH
                else:
                    num_frames = 2
                    frame_rule = 42
                    self.frames_since_last_change += 1
                    if self.frames_since_last_change >= frame_rule:
                        self.frames_since_last_change = 0
                    elif self.frames_since_last_change >= frame_rule//2:
                        self.engine.sprite_db.get_sprite(self, new_col = 6)
                    else:
                        self.engine.sprite_db.get_sprite(self, new_col = 5)
            case ObjectState.VORTEX:
                num_frames = 1
                frame = int(num_frames*timer_manager.get_progress(f"player_move"))
                if frame >= num_frames:
                    if self.hp > 0:
                        if self.body_status_ex == ExternalBodyStatus.ON_FIRE:
                            self.state = ObjectState.BURNING
                        else:
                            self.state = ObjectState.STAND
                    else:
                        self.state = ObjectState.DEATH
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = 4)
            case ObjectState.WALK:
                num_frames = 1
                frame = int(num_frames*timer_manager.get_progress(f"player_move"))
                if frame >= num_frames:
                    self.state = ObjectState.STAND
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = self.engine.step_tracker + 1)
    
    def get_total_power(self) -> int:
        """Get total attack power including weapon"""
        base_power = self.strength
        weapon = self.equipped.get(EquipmentSlot.WEAPON.value)
        if weapon:
            base_power += weapon.power
        return base_power
    
    def get_total_guard(self) -> int:
        """Get total defense including armor"""
        base_guard = self.dexterity // 2  # Base defense from dexterity
        armor = self.equipped.get(EquipmentSlot.ARMOR.value)
        if armor:
            base_guard += armor.guard
        return base_guard
    
    def trigger_equipment_effects(self, trigger: EffectTrigger, context: Dict[str, Any] = None) -> List[str]:
        """Trigger equipment effects and return descriptions of what happened"""
        if context is None:
            context = {}
        
        results = []
        
        for equipment in self.equipped.values():
            if equipment is None:
                continue
                
            for effect in equipment.effects:
                if effect.trigger == trigger:
                    result = self.execute_equipment_effect(effect, context)
                    if result:
                        results.append(f"{self.name}'s {equipment.name}: {result}")
        
        return results
    
    def execute_equipment_effect(self, effect: ItemEffect, context: Dict[str, Any]) -> Optional[str]:
        """Execute a specific equipment effect"""
        if effect.effect_type == EffectType.ON_ATTACK_HEAL and effect.trigger == EffectTrigger.ON_ATTACK:
            target = context.get("target")
            damage_dealt = context.get("damage_dealt", 0)
            
            if target and damage_dealt > 0:  # Only heal if damage was dealt
                heal_amount = min(effect.value, self.max_hp - self.hp)
                self.hp += heal_amount
                return f"Healed {heal_amount} HP"
        
        elif effect.effect_type == EffectType.ON_DEFEND_DAMAGE and effect.trigger == EffectTrigger.ON_DEFEND:
            attacker = context.get("attacker")
            if attacker:
                damage = min(effect.value, attacker.hp)
                attacker.hp -= damage
                return f"Reflected {damage} damage"
        
        return None
    
    def can_cast(self, spell: 'Spell') -> bool:
        if spell.mp_cost > self.mp:
            print("Not enough MP!!!")
            return False
        if spell.virtue not in self.virtue_manager.virtues:
            print("Sorry, that class doesn't exist.")
            return False
        if spell.level < self.virtue_manager.virtues[spell.virtue]["level"]:
            print("I'm not pious engough")
            return False
        return True
    
    def prep_spell(self, spell: 'Spell' = None):
        self.engine.revert_state()
        if not spell:
            self.engine.oops = "Your prayer was recognized by none of Sewinso's deities."
            return False
        if self.can_cast(spell):
            print("HELLO")
            match self.engine.state:
                case GameState.COMBAT:
                    match spell.target_type:
                        case TargetType.SELF:
                            self.prepped_spell = spell
                            self.cast_spell(party_member = self)
                        case TargetType.DIRECTION:
                            self.engine.spell_direction_mode = True
                            self.prepped_spell = spell
                            range_min = max(spell.range_min, 1)
                            range_max = spell.range + 1
                            if "cardinal" in spell.args:
                                for i in range(range_min, range_max):
                                    for offset in [(i, 0), (0, i), (-i, 0), (0, -i)]:
                                        tpos = self.add_tuples(self.position, offset)
                                        if self.engine.current_map.in_map_range(tpos):
                                            self.engine.current_map.set_tile(tpos, self.engine.tile_db.get_tile("targettile"))
                            if "diagonal" in spell.args:
                                for i in range(spell.range_min, spell.range+1):
                                    for offset in [(i, i), (-i, i), (-i, -i), (i, -i)]:
                                        tpos = self.add_tuples(self.position, offset)
                                        if self.engine.current_map.in_map_range(tpos):
                                            self.engine.current_map.set_tile(tpos, self.engine.tile_db.get_tile("targettile"))
                            self.engine.combat_manager.append_to_combat_log(f"Press desired direction for {spell.name}.")
                        case TargetType.TARGET:
                            self.engine.spell_target_mode = True
                            self.engine.cursor_position = self.position
                            self.prepped_spell = spell
                            self.engine.use_range = spell.range
                            cam_x, cam_y = self.engine.camera
                            base_tile = (int(cam_x), int(cam_y))
                            for y in range(MAP_HEIGHT + 1):  # +1 to cover partial bottom row
                                for x in range(MAP_WIDTH + 1):  # +1 to cover partial right column
                                    tx, ty = self.add_tuples(base_tile, (x, y))
                                    if (abs(self.position[0] - tx) + abs(self.position[1] - ty)) < self.prepped_spell.range:
                                        self.engine.current_map.set_tile((tx, ty), self.engine.tile_db.get_tile("targettile"))
                            self.engine.combat_manager.append_to_combat_log(f"Select target of {spell.name} (within a range of {spell.range}.)")
                        case TargetType.SELF_AREA:
                            position = self.position
                            self.engine.spell_self_mode = True
                            self.prepped_spell = spell
                            if "offset_layers" in spell.args:
                                for offset_layer in spell.args["offset_layers"]:
                                    for offset in offset_layer["offsets"]:
                                        tpos = self.add_tuples(position, offset)
                                        if self.engine.current_map.in_map_range(tpos):
                                            self.engine.current_map.set_tile(tpos, self.engine.tile_db.get_tile("areatile"))
                                self.engine.combat_manager.append_to_combat_log(f"Cast {spell.name}? (Press Enter to confirm)")
                                return
                            y_min = max(0, position[1] - self.prepped_spell.range)
                            y_max = min(MAP_HEIGHT+1, position[1] + self.prepped_spell.range)
                            x_min = max(0, position[0] - self.prepped_spell.range)
                            x_max = min(MAP_WIDTH+1, position[0] + self.prepped_spell.range)
                            for y in range(y_min, y_max):  # +1 to cover partial bottom row
                                for x in range(x_min, x_max):  # +1 to cover partial right column
                                    tx, ty = self.add_tuples(base_tile, (x, y))
                                    if (abs(position[0] - tx) + abs(position[1] - ty)) < self.prepped_spell.range:
                                        self.engine.current_map.set_tile((tx, ty), self.engine.tile_db.get_tile("areatile"))

                case GameState.TOWN:
                    match spell.target_type:
                        case TargetType.DIRECTION:
                            self.engine.oops = "This prayer shant be answered lest thou art in peril."
                            return False
                        case TargetType.TARGET:
                            self.engine.spell_target_mode = True
                            self.prepped_spell = spell
                            self.engine.oops = f"Press number key of ally to cast upon (1-9) or the direction of adjacent entity."
            return True
        return False
    
    def cast_spell(self, direction: Direction = None, position: tuple[int, int] = None, party_member: 'Character' = None):
        spell = self.prepped_spell
        if not spell:
            return
        
        virtue = spell.virtue
        # Check for spell failure penalty
        failure_chance = 0#self.virtue_manager._get_spell_failure_chance(virtue)
        if failure_chance > 0:
            import random
            if random.randint(1, 100) <= failure_chance:
                self.engine.combat_manager.append_to_combat_log(f"Though {party_member.name}'s lips move, {party_member.pronoun} make no sound!")
                # Casting the spell at all still gives you overuse points, whether it works or not.
                self.virtue_manager.add_overuse(virtue, spell.overuse_cost)
        
        if direction:
            self.mp -= spell.mp_cost
            spell.cast_in_direction(self, direction.value)
        elif position:
            self.mp -= spell.mp_cost
            spell.cast_at_position(self, position)
        elif party_member:
            self.mp -= spell.mp_cost
            print("Debug: Arrive at cast on party member")
            spell.cast_on_party_member(self, party_member)
        else:
            self.engine.combat_manager.append_to_combat_log("I don't know how to cast this spell")
            return
        # Cast spell successfully
        overuse_exceeded = self.virtue_manager.add_overuse(virtue, spell.overuse_cost)
        self.virtue_used_this_turn = virtue
        self.engine.combat_manager.append_to_combat_log(f"Cast {spell.name}!")
        
        if overuse_exceeded:
            self.engine.combat_manager.append_to_combat_log(f"Overuse threshold exceeded for {virtue.value}!")
        self.engine.combat_manager.player_actioned = True
        if self.engine.combat_manager.player_moved:
            self.engine.combat_manager.conclude_current_player_turn()
        
    def attacked(self, attacker, damage):
        self.engine.combat_manager.append_to_combat_log(f"{attacker.name} hit {self.name} for {damage} damage!")
    
    def to_dict(self):
        data = {"hp" : self.hp, "max_hp" : self.max_hp, "position" : self.position, "old_position" : self.old_position, "fixed_spritesheet_row": self.fixed_spritesheet_row, "experience" : self.experience, "args" : copy.deepcopy(self.args)}
        # Convert equipped items to dict format
        equipped_dict = {}
        for slot, equipment in self.equipped.items():
            if equipment:
                equipped_dict[slot] = equipment.item_id
            else:
                equipped_dict[slot] = None
        data["args"]["equipped"] = equipped_dict
        if "spritesheet" in data["args"]:
            data["args"]["spritesheet"] = [data["args"]["spritesheet"][0], 0, 0]
        return data
    
    @classmethod
    def from_dict(cls, name, data, engine: 'GameEngine', load_dict: dict = {}):
        data = data | load_dict
        data["name"] = name
        if "hp" not in data and "max_hp" in data:
            data["hp"] = data["max_hp"]
        if "mp" not in data and "max_mp" in data:
            data["mp"] = data["max_mp"]
        if "position" in data:
            data["position"] = tuple(data["position"])
        character = cls(**data)
        character.engine = engine
        character.map = character.engine.current_map
        # Load equipped items
        equipped_data = data.get("args", {}).get("equipped", {})
        for slot, equipment_data in equipped_data.items():
            if equipment_data:
                equipment = engine.item_db.create_item(equipment_data)
                character.equip_item(equipment)
        
        return character
    
    def start_bump_animation(self, direction):
        """Start the bump animation for a character"""
        # Store the bump direction and current position
        self.old_position = self.position
        self.bump_direction = direction
        self.is_bumping = True
        
        # Set up the bump timer (shorter than normal movement)
        self.engine.event_manager.timer_manager.start_timer("player_bump", 170)

        

# Modified Party Class
class Party:
    def __init__(self, engine: 'GameEngine'):
        self.engine: 'GameEngine' = engine
        self.members: List[Character] = []
        self.inventory: List[Item] = []
        self.last_move_direction: tuple[int, int] = None
        self.gold: int = 100
        self.foreign_word_dict: dict[str, str] = {"eres" : "are you", "como" : "like"}
        self.god_favor: int = 4
        self.current_map = "overworld"
    def empty_party(self):
        self.members = []
        self.inventory = []
    def add_member(self, name: str, data: dict):
        if len(self.members) < 7:  # Ultima 4 party limit
            character = Character.from_dict(name, data, self.engine)
            self.members.append(character)
            
    def get_leader(self) -> Optional[Character]:
        return self.members[0] if self.members else None
    
    def move(self, direc: tuple[int, int], game_map: 'Map') -> Tuple[bool, int]:
        leader = self.get_leader()
        if not leader:
            raise Exception(f"Leader does not exist")
        new_pos = leader.add_tuples(leader.position, direc)
        if game_map.is_passable(new_pos, leader.position):
            # Update party positions for following behavior
            leader.state = ObjectState.WALK
            self.last_move_direction = direc
            self.engine.step_tracker = 1 - self.engine.step_tracker
            if not self.engine.event_manager.timer_manager.is_active("player_move"):
                self.engine.event_manager.timer_manager.start_timer("player_move", 270)
            else:
                self.engine.event_manager.timer_manager.timers["player_move"]["duration"] += 270
            tile_sound_name = game_map.get_tile_lower(new_pos).step_sound
            tile_sound = tile_sound_name + "_" + str(self.engine.step_tracker)
            if tile_sound in self.engine.sound_manager.sound:
                self.engine.sound_manager.sound[tile_sound].play()
            leader.old_position = leader.position
            leader.position = new_pos
            movement_penalty = DEFAULT_MOVEMENT_PENALTY
            if game_map.name == "overworld":
                movement_penalty = DEFAULT_OVERWORLD_MOVEMENT_PENALTY
            return True, movement_penalty
        if 0 <= new_pos[0] < self.engine.current_map.width and 0 <= new_pos[1] < self.engine.current_map.height:
            return False, 0 
        warp_map_obj = self.engine.current_map.get_object_by_name("map_edge_teleporter")
        if not warp_map_obj:
            return False, 0
        new_map_instructions = warp_map_obj.args.get("adjacent_maps")
        if not new_map_instructions:
            return False, 0
        for key in new_map_instructions.keys():
            if direc == self.engine.get_direction(key).value:
                self.last_move_direction = direc
                new_map_direction = new_map_instructions[key]
                #FINALLY, we can tell the game to warp us to the next map... once we tell it what that is.
                if type(new_map_direction) == list:
                    
                    for d in new_map_direction:
                        if key in ["E", "W"] and d["range"][0] <= new_pos[0] <= d["range"][1]:
                            return self.edge_teleport(d, leader)
                        elif key in ["N", "S"] and d["range"][0] <= new_pos[1] <= d["range"][1]:
                            return self.edge_teleport(d, leader)
                            
                return self.edge_teleport(new_map_direction, leader)
        return False, 0

                    
                    
    def edge_teleport(self, new_map_instructions: dict, leader: Character):
        new_map = new_map_instructions["map"]
        if new_map not in self.engine.maps:
            if not self.engine.load_map(new_map):
                self.engine.append_to_message_log(f"Error: Could not find map {new_map}")
                return False, 0
        pos = new_map_instructions.get("position", None)
        if pos:
            leader.position = ast.literal_eval(pos)
        offset = new_map_instructions.get("offset", None)
        if "offset" in new_map_instructions:
            print(self.last_move_direction, Direction(self.last_move_direction))
            match Direction(self.last_move_direction):
                case Direction.SOUTH:
                    new_pos = (leader.position[0], 0)
                case Direction.NORTH:
                    new_pos = (leader.position[0], self.engine.maps[new_map].height-1)
                case Direction.EAST:
                    new_pos = (0, leader.position[1])
                case Direction.WEST:
                    new_pos = (self.engine.maps[new_map].width-1, leader.position[1])
            new_pos = leader.add_tuples(new_pos, ast.literal_eval(offset))
            if not self.engine.maps[new_map].is_passable(new_pos):
                return False, 0
            leader.position = new_pos
        if pos or offset:
            print(leader.position)
            for i in self.members:
                self.engine.current_map.objects.remove(i)
            self.engine.current_map = self.engine.maps[new_map]
            self.current_map = new_map
            for i in self.members:
                self.engine.current_map.add_object(i)
        for obj in self.engine.current_map.objects:
            obj.on_map_load()
        npc_move_intervals = {}
        for obj in self.engine.current_map.get_objects_subset(MapObject):
            npc_move_intervals[obj.name] = obj.move_interval
        results = self.engine.schedule_manager.process_map_load(npc_move_intervals)
        return True, DEFAULT_MOVEMENT_PENALTY
        
    
    def get_party_member_position(self, member_index: int):
        """Get the position for a specific party member"""
        if member_index < len(self.members):
            party_member = self.members[member_index]
            return party_member.position
        return 0, 0
    
    def set_party_member_position(self, member_index: int, pos: tuple[int, int]):
        """Get the position for a specific party member"""
        if member_index < len(self.members):
            self.members[member_index].old_position = self.members[member_index].position
            self.members[member_index].position = pos
            
        
    def add_item(self, item: Item):
        # Check if item already exists
        if self.inventory and item:
            for existing_item in self.inventory:
                if existing_item.name == item.name:
                    existing_item.quantity += item.quantity
                    return
        self.inventory.append(item)
        return item
    
    def add_item_by_id(self, item_id: str, quantity: int = 1):
        return self.add_item(self.engine.item_db.create_item(item_id, quantity))
    
    def check_for_item_by_id(self, item_id: str):
        for item in self.inventory:
            if item_id == item.item_id:#Lowercase so the user's input isn't invalid if they missed a case.
                return item
        return False
    
    def check_for_item_by_name(self, item_name: str):
        item_name_lower = item_name.lower()
        for item in self.inventory:
            if item_name_lower == item.name.lower():#Lowercase so the user's input isn't invalid if they missed a case.
                return True
        return False
    
    def remove_item(self, item: Item, quantity: int = 1, allow_failure: bool = False):
        """Remove item from party inventory"""
        if item in self.inventory:
            if item.quantity > quantity:
                item.quantity -= quantity
                return True
            if item.quantity == quantity or allow_failure:
                self.inventory.remove(item)
                return True
        return False
    
    def remove_item_by_id(self, item_id: str, quantity: int = 1, allow_failure: bool = False):
        """Remove equipment from party inventory"""
        for item in self.inventory:
            if item.item_id == item_id:
               return self.remove_item(item, quantity, allow_failure)
        return False
        
    def to_dict(self):
        return {
            "members": {member.name : member.to_dict() for member in self.members},
            "inventory": {item.item_id : item.quantity for item in self.inventory},
            "current_map" : self.current_map,
            "gold": self.gold
        }
    
    @classmethod
    def from_dict(cls, data, engine: 'GameEngine'):
        party = cls(engine)
        party.members = [Character.from_dict(name, member_data, engine) for name, member_data in data.get("members", {}).items()]
        for item_id, quantity in data.get("inventory", {}).items():
            party.add_item_by_id(item_id, quantity)
        party.gold = data.get("gold", 100)
        return party