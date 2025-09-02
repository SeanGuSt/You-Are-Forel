from dataclasses import dataclass, asdict, field
import json
from typing import List, Dict, Any, Optional, Type, TYPE_CHECKING
from constants import EffectType, EquipmentSlot, EffectTrigger
ITEM_REGISTRY: Dict[str, Type['Item']] = {}
if TYPE_CHECKING:
    from objects.characters import Character
    from ultimalike import GameEngine

def register_item_type(name: str):
    def decorator(cls):
        ITEM_REGISTRY[name] = cls
        return cls
    return decorator
class ItemDatabase:
    def __init__(self):
        self.item_templates = ITEM_REGISTRY
        self.items = {}
        self.load_items()
    
    def load_items(self):
        """Load item templates - these define what each item type IS"""
        # This could be from JSON, but for simplicity, defined here
        with open("items/items.json", 'r') as f:
            templates = json.load(f)
        
        # Convert to ItemTemplate objects
        for item_id, properties in templates.items():
            cls = self.item_templates.get(properties.get("item_type", ""), None)
            if cls:
                self.items[item_id] = cls.from_dict(properties)
                self.items[item_id].item_id = item_id
    
    def create_item(self, item_id: str, quantity: int = 0) -> 'Item':
        item = self.items.get(item_id, None)
        if item and quantity:
            item.quantity = quantity
        return item
    
@dataclass
class ItemEffect:
    effect_type: EffectType
    trigger: EffectTrigger
    value: int
    stat_name: Optional[str] = None  # For stat buffs: "strength", "hp", etc.
    description: str = ""
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            effect_type=EffectType(data["effect_type"]),
            trigger=EffectTrigger(data["trigger"]),
            value=data["value"],
            stat_name=data.get("stat_name"),
            description=data.get("description", "")
        )
@register_item_type("item")
@dataclass
class Item:
    name: str
    description: str
    uid: int
    item_id = ""
    plural: str = ""
    quantity: int = 1
    slot: EquipmentSlot = None#Equipmentslot
    value: int = 0#Price
    power: int = 0
    guard: int = 0
    max_hp: int = 0
    weight: int = 0
    max_stack: int = 7
    omit_article: bool = False
    is_usable: bool = True
    consume_upon_use: bool = True
    is_discardable: bool = True
    can_be_sold: bool = True
    effect: str = ""
    evalues: list[int] = field(default_factory=lambda: [])
    estats: list[str] = field(default_factory=lambda: [])
    effects: list[EffectType] = field(default_factory=lambda: [])
    triggers: list[EffectTrigger] = field(default_factory=lambda: [])
    item_type: str = "consumable"  # New field to distinguish item types
    instance_data: Dict[str, Any] = None

    def __post_init__(self):
        if not self.plural:
            self.plural = self.name
        if self.effects is None:
            self.effects = []

    def to_dict(self):
        return {self.item_id : self.quantity}

    @classmethod
    def from_dict(cls, data: dict, quantity: int = 1) -> 'Item':
        item_type = data.get("item_type")
        all_effects = data.pop("effects", None)
        if "quantity" not in data:
            data["quantity"] = quantity
        item = cls(**data)
        if all_effects:
            for effect in all_effects:
                etrigger, etype, estats, evalue = effect.split("__")
                item.effects.append(EffectType(etype))
                item.triggers.append(EffectTrigger(etrigger))
                item.estats.append(estats)
                item.evalues.append(int(evalue))

        return item

@register_item_type("consumable")
@dataclass
class Consumable(Item):
    pass

@register_item_type("keyitem")
@dataclass
class KeyItem(Item):
    is_usable: bool = False
    can_be_sold: bool = False
    is_discardable: bool = False

@register_item_type("equipment")
@dataclass
class Equipment(Item):
    special_attacks = []
    def circle_sweep(self, master: 'Character', radius: int = 1, include_self: bool = False, hit_allies: bool = True, edge_only: bool = True):
        """Perform a circle sweep attack around the character."""
        radius_plus_one = radius + 1
        for dx in range(radius_plus_one):
            for dy in range(radius_plus_one):
                if not include_self and not (dx or dy):
                    continue
                if edge_only:
                    if dx + dy != radius_plus_one:
                        continue
                if dx + dy <= radius_plus_one:
                    # Calculate the position relative to the master character
                    pos = (master.x + dx, master.y + dy)
                    self.perform_special_attack(master, pos, hit_allies)
                    if dx:
                        pos = (master.x - dx, master.y + dy)
                        self.perform_special_attack(master, pos, hit_allies)
                    if dy:
                        pos = (master.x + dx, master.y - dy)
                        self.perform_special_attack(master, pos, hit_allies)

                        if dx and dy:#Don't bother with this one if not dy.
                            pos = (master.x - dx, master.y - dy)
                            self.perform_special_attack(master, pos, hit_allies)

    def perform_special_attack(self, master: 'Character', pos: tuple[int, int], hit_allies: bool = True):
        for obj in master.engine.current_map.get_objects_at(pos):
            if hit_allies or obj.is_hostile:
                obj.attacked(master, self.power)
                return
    pass

@register_item_type("weapon_melee")
@dataclass
class Weapon_Melee(Equipment):
    slot: EquipmentSlot = EquipmentSlot.WEAPON

@register_item_type("weapon_ranged")
@dataclass
class Weapon_Ranged(Equipment):
    slot: EquipmentSlot = EquipmentSlot.RANGED

@register_item_type("armor")
@dataclass
class Armor(Equipment):
    slot: EquipmentSlot = EquipmentSlot.ARMOR
    omit_article: bool = True

@register_item_type("accessory")
@dataclass
class Accessory(Equipment):
    slot: EquipmentSlot = EquipmentSlot.ACCESSORY
        