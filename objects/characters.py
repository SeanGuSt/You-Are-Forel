from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Any, Optional, TYPE_CHECKING
from items.itemz import Item, ItemEffect, ItemDatabase, Equipment
from constants import *
import copy
from magic.virtue import VirtueManager, VirtueType

from objects.object_templates import Node, CombatStatsMixin
if TYPE_CHECKING:
    from objects.map_objects import Map
    from magic.magic import Spell
    from ultimalike import GameEngine

# Modified Character Class
@dataclass
class Character(CombatStatsMixin, Node):
    level: int = 1
    hp: int = 100
    max_hp: int = 100
    mp: int = 50#Ignore
    max_mp: int = 50#Ignore
    strength: int = 10
    dexterity: int = 10
    faith: int = 10
    experience: int = 0
    gold: int = 100
    last_move_direction: tuple[int, int] = (0, 0)
    special: bool = False
    is_passable: bool = False
    prepped_spell: 'Spell' = None
    
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
        
        # Unequip previous item
        if previously_equipped:
            self.apply_equipment_effects(previously_equipped, unequip=True)
        
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
                    if (not unequip and estat == "+") or (unequip and estat == "-"):
                        is_delta = True
                    elif (not unequip and estat == "-") or (unequip and estat == "+"):
                        is_delta = True
                        evalue = -evalue
                    self.engine.sprite_db.get_sprite(self, new_row = evalue, is_delta = is_delta)
    
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
        if spell.level < self.virtue_manager.virtues[spell.virtue].level:
            print("I'm not pious engough")
            return False
        return True
    
    def prep_spell(self, spell: 'Spell' = None):
        self.engine.revert_state()
        if not spell:
            print("I cant do this spell for some reason.")
            self.engine.oops = "Your prayer was recognized by none of Sewinso's deities."
            return False
        if self.can_cast(spell):
            print("HELLO")
            match self.engine.state:
                case GameState.COMBAT:
                    match spell.target_type:
                        case TargetType.DIRECTION:
                            self.engine.spell_direction_mode = True
                            self.prepped_spell = spell
                            self.engine.use_range = spell.range
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
        result = {
            'success': False,
            'message': '',
            'overuse_triggered': False,
            'penalty_applied': False
        }
        
        virtue = spell.virtue
        # Check for spell failure penalty
        failure_chance = self.virtue_manager._get_spell_failure_chance(virtue)
        if failure_chance > 0:
            import random
            if random.randint(1, 100) <= failure_chance:
                result['message'] = f"Spell failed due to {virtue.value} overuse!"
                # Casting the spell at all still gives you overuse points, whether it works or not.
                self.virtue_manager.add_overuse_points(virtue, spell.overuse_cost)
                return result
        
        
        if direction:
            self.mp -= spell.mp_cost
            spell.cast_in_direction(self, direction.value)
        elif position:
            self.mp -= spell.mp_cost
            spell.cast_at_position(self, position)
        elif party_member:
            self.mp -= spell.mp_cost
            spell.cast_on_party_member(self, party_member)
        else:
            self.engine.oops = "I don't know how to cast this spell"
            return
        # Cast spell successfully
        overuse_exceeded = self.virtue_manager.add_overuse_points(virtue, spell.overuse_cost)
        self.virtue_used_this_turn = virtue
        
        result['success'] = True
        result['message'] = f"Cast {spell.name}!"
        
        if overuse_exceeded:
            result['overuse_triggered'] = True
            result['message'] += f" Overuse threshold exceeded for {virtue.value}!"
        
        self.engine.combat_manager.advance_turn()
        return result
        
    def attacked(self, attacker, damage):
        self.engine.combat_manager.append_to_combat_log(f"{attacker.name} hit {self.name} for {damage} damage!")
    
    def to_dict(self):
        data = {"hp" : self.hp, "mp" : self.mp, "x" : self.x,  "y" : self.y, "position" : self.position, "old_position" : self.old_position, "experience" : self.experience, "args" : copy.deepcopy(self.args)}
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
    def add_member(self, character: Character):
        if len(self.members) < 7:  # Ultima 4 party limit
            self.members.append(character)
            
    def get_leader(self) -> Optional[Character]:
        return self.members[0] if self.members else None
    
    def move(self, direc: tuple[int, int], game_map: 'Map') -> Tuple[bool, int]:
        leader = self.get_leader()
        new_pos = leader.add_tuples(leader.position, direc)
        if game_map.is_passable(new_pos):
            # Update party positions for following behavior
            self.last_move_direction = direc
            self.engine.step_tracker = 1 - self.engine.step_tracker
            tile_sound_name = game_map.get_tile_lower(new_pos).step_sound
            tile_sound = tile_sound_name + "_" + str(self.engine.step_tracker)
            self.engine.sprite_db.get_sprite(leader, new_col = self.engine.step_tracker + 1)
            if tile_sound in self.engine.sound_manager.sound:
                self.engine.sound_manager.sound[tile_sound].play()
            leader.old_position = leader.position
            leader.position = new_pos
            movement_penalty = DEFAULT_MOVEMENT_PENALTY
            if game_map.name == "overworld":
                movement_penalty = DEFAULT_OVERWORLD_MOVEMENT_PENALTY
            self.engine.event_manager.timer_manager.start_timer("player_move", 275)
            return True, movement_penalty
        return False, 0
    
    def get_party_member_position(self, member_index: int):
        """Get the position for a specific party member"""
        if member_index < len(self.members):
            party_member = self.members[member_index]
            return party_member.x, party_member.y
        return 0, 0
    
    def set_party_member_position(self, member_index: int, x: int | tuple[int, int], y: int | None = None):
        """Get the position for a specific party member"""
        if member_index < len(self.members):
            if not y:
                self.members[member_index].old_position = self.members[member_index].position
                self.members[member_index].position = x
                return

            self.members[member_index].x, self.members[member_index].y = x, y
            self.members[member_index].old_position = self.members[member_index].position
            self.members[member_index].position = (x, y)
            
        
    def add_item(self, item: Item):
        # Check if item already exists
        if self.inventory and item:
            for existing_item in self.inventory:
                if existing_item.name == item.name:
                    existing_item.quantity += item.quantity
                    return
        self.inventory.append(item)
    
    def add_item_by_name(self, item_name: str, quantity: int = 1):
        self.add_item(self.engine.item_db.create_item(item_name, quantity))
    
    def remove_item(self, item: Item, quantity: int = 1, allow_failure: bool = False):
        """Remove equipment from party inventory"""
        if item in self.inventory:
            if item.quantity > quantity:
                item.quantity -= quantity
                return True
            if item.quantity == quantity or allow_failure:
                self.inventory.remove(item)
                return True
        return False
    
    def remove_item_by_name(self, item_name: str, quantity: int = 1, allow_failure: bool = False):
        """Remove equipment from party inventory"""
        for item in self.inventory:
            if item.name == item_name:
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
            party.add_item_by_name(item_id, quantity)
        party.gold = data.get("gold", 100)
        return party