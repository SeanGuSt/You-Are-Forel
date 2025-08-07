from typing import Optional, List, Any, Dict, Type, TYPE_CHECKING
from dataclasses import dataclass, field
from constants import GameState, TargetType, EffectType, VirtueType, DamageType, MAGIC_DIR
from magic.virtue import Virtue
from objects.map_objects import MapObject, Monster
import os, json
# New spell system
if TYPE_CHECKING:
    from objects.characters import Character
    from ultimalike import GameEngine
SPELL_REGISTRY: Dict[str, Type['Spell']] = {}
def register_spell_type(name: str):
    def decorator(cls):
        SPELL_REGISTRY[name] = cls
        return cls
    return decorator

@register_spell_type("spell")
@dataclass
class Spell:
    name: str
    overuse_cost: int
    target_type: TargetType
    effect_type: EffectType
    damage_type: DamageType
    args: dict[str, Any] = field(default_factory=lambda: {})
    magic_word: str = ""
    power: int = 1
    range: int = 1
    level: int = 1
    virtue: VirtueType = None
    unlocked: bool = True
    mp_cost: int = 0

    def cast_in_direction(self, caster: 'Character', direction: tuple[int, int]):
        spell_target = caster.x, caster.y
        for i in range(self.range):
            spell_target = tuple(a + b for a, b in zip(spell_target, direction))
            for obj in caster.engine.current_map.get_objects_at(spell_target):
                if type(obj) == MapObject:
                    self.do_effect(obj, caster)

    def cast_at_position(self, caster: 'Character', position: tuple[int, int]):
        for obj in caster.engine.current_map.get_objects_at(position, subtype = Monster):
            if obj.hp > 0:
                self.do_effect(obj, caster)
                break

    def cast_on_party_member(self, caster: 'Character', target: 'Character'):
        self.do_effect(target, caster)
        print(f"{caster.name} has healed {target.name} for {self.power}")
    
    def do_effect(self, target, caster):
        match self.effect_type:
            case EffectType.HEAL:
                target.hp = min(target.hp + self.power, target.max_hp)
            case EffectType.DAMAGE:
                target.hp -= self.power
                if target.hp <= 0:
                    target.map.remove_object(target)
                else:
                    target.attacked(caster, self.power)
    @classmethod
    def from_dict(cls, data: dict):
        spell_type = data.pop("spell_type", "spell")
        data["target_type"] = TargetType(data["target_type"])
        data["effect_type"] = EffectType(data["effect_type"])
        data["damage_type"] = DamageType(data["damage_type"])
        data["virtue"] = VirtueType(data["virtue"])
        return cls(**data)
    

@dataclass
class SpellBook:
    def __init__(self, game_engine: 'GameEngine'):
        self.spells = {}
        self.spell_templates = SPELL_REGISTRY
        self.load_spells()
        self.engine = game_engine
        self.target_mode = False
        self.direction_mode = False
    
    def get_spell(self, name: str) -> Optional[Spell]:
        return self.spells.get(name.lower())
    
    def get_available_spells(self) -> List[str]:
        return list(self.spells.keys())
    
    def load_spells(self):
        spell_path = "magic.json"
        spell_path = os.path.join(MAGIC_DIR, spell_path)
        if not os.path.exists(spell_path):
            return
        with open(spell_path, 'r', encoding='utf-8') as f:
            templates = json.load(f)
        
        # Convert to ItemTemplate objects
        for magic_word, properties in templates.items():
            spell_type = properties.pop("spell_type", "spell")
            cls = self.spell_templates.get(spell_type, None)
            if cls:
                self.spells[magic_word] = cls.from_dict(properties)
                self.spells[magic_word].magic_word = magic_word
    
    def process_user_input(self, input_text: str) -> Spell:
        input_lower = input_text.lower().strip()

        return self.spells.get(input_lower, None)
    

    




