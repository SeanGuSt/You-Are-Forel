from dataclasses import dataclass, asdict, field
import json
from typing import List, Dict, Any, Optional, Type
from constants import EffectType, EquipmentSlot, EffectTrigger
ITEM_REGISTRY: Dict[str, Type['Item']] = {}

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
    quantity: int = 1
    slot = None
    value: int = 0
    power: int = 0
    guard: int = 0
    weight: int = 0
    max_stack: int = 7
    is_discardable: bool = True
    effect: str = ""
    evalues: list[int] = field(default_factory=lambda: [])
    estats: list[str] = field(default_factory=lambda: [])
    effects: list[EffectType] = field(default_factory=lambda: [])
    triggers: list[EffectTrigger] = field(default_factory=lambda: [])
    item_type: str = "consumable"  # New field to distinguish item types
    instance_data: Dict[str, Any] = None

    def __post_init__(self):
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

@register_item_type("equipment")
@dataclass
class Equipment(Item):
    pass

@register_item_type("weapon_melee")
@dataclass
class Weapon_Melee(Equipment):
    slot = EquipmentSlot.WEAPON

@register_item_type("weapon_ranged")
@dataclass
class Weapon_Ranged(Equipment):
    slot = EquipmentSlot.RANGED

@register_item_type("armor")
@dataclass
class Armor(Equipment):
    slot = EquipmentSlot.ARMOR

@register_item_type("accessory")
@dataclass
class Accessory(Equipment):
    slot = EquipmentSlot.ACCESSORY
        