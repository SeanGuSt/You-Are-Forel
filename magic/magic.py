from typing import Optional, List, Any, Dict, Type, TYPE_CHECKING
from dataclasses import dataclass, field
from constants import GameState, TargetType, EffectType, VirtueType, DamageType, MAGIC_DIR, ExternalBodyStatus, ObjectState
from magic.virtue import Virtue
from objects.object_templates import MapObject, Monster, CombatStatsMixin
import random
import os, json, ast
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
    hurt_caster: bool = False
    args: dict[str, Any] = field(default_factory=lambda: {})
    magic_word: str = ""
    power: int = 1
    range_min: int = 0
    range: int = 1
    level: int = 1
    virtue: VirtueType = None
    unlocked: bool = True
    mp_cost: int = 0

    def cast_in_direction(self, caster: 'Character', direction: tuple[int, int]):
        spell_target = caster.position
        if self.effect_type == EffectType.MOVE:
            move_dist = random.randint(self.range_min, self.range)
            caster.old_position = caster.position
            caster.position = caster.add_tuples(spell_target, caster.multiply_tuples(direction, move_dist))
            caster.state = ObjectState.VORTEX
            caster.engine.event_manager.timer_manager.start_timer("player_move", 80*move_dist)
        for i in range(self.range):
            spell_target = tuple(a + b for a, b in zip(spell_target, direction))
            for obj in caster.engine.current_map.get_objects_at(spell_target):
                if type(obj) == MapObject:
                    self.do_effect(obj, caster)

    def cast_at_position(self, caster: 'Character', position: tuple[int, int]):
        for obj in caster.engine.current_map.get_objects_at(position, subtype = CombatStatsMixin):
            if obj.hp > 0:
                self.do_effect(obj, caster)
                break

    def cast_on_party_member(self, caster: 'Character', target: 'Character'):
        self.do_effect(target, caster)
    
    def do_effect(self, target: CombatStatsMixin, caster: CombatStatsMixin):
        match self.effect_type:
            case EffectType.HEAL:
                target.hp = min(target.hp + self.power, target.max_hp)
            case EffectType.DAMAGE:
                target.hp -= self.power
                target.attacked(caster, self.power)
            case EffectType.AREA_DAMAGE:
                caster.state = ObjectState.STAFF_SLAM
                print("Debug: Arrived at area damage effect type")
                if "offset_layers" in self.args:
                    start_delay = 0
                    item_num = -1
                    for offset_layer in self.args["offset_layers"]:
                        start_delay += offset_layer["delay"]
                        new_properties = {"x" : 0, "y" : 0, "args" : {"delay" : start_delay}}
                        for offset in offset_layer["offsets"]:
                            print("Debug: Offsets found")
                            item_num += 1
                            new_properties["x"], new_properties["y"] = caster.add_tuples(target.position, offset)
                            obj = target.engine.map_obj_db.create_obj(f"{offset_layer["spawn"]}_{item_num}", offset_layer["spawn"], new_properties)
                            target.engine.current_map.add_object(obj)
                            obj.map = target.engine.current_map



            case EffectType.BODY_BURN:
                if not target.engine.state == GameState.COMBAT:
                    raise Exception("body_burn should not be inflicted outside combat")
                target.body_status_ex = ExternalBodyStatus.ON_FIRE
                target.body_status_ex_counter = self.power
                target.engine.combat_manager.append_to_combat_log(f"{target.name} has been set ablaze!")
                if target.parasite_ex and target.parasite_ex.dies_if_host_on_fire:
                    target.engine.sprite_db.get_sprite(target.parasite_ex, 0, 1)
                    target.parasite_ex.hp = -999#Important note: this does not count as dealing damage, hence setting the value
                    target.parasite_ex.attacked(target)
                    


    @classmethod
    def from_dict(cls, data: dict):
        spell_type = data.pop("spell_type", "spell")
        data["target_type"] = TargetType(data["target_type"])
        data["effect_type"] = EffectType(data["effect_type"])
        data["damage_type"] = DamageType(data["damage_type"])
        data["virtue"] = VirtueType(data["virtue"])
        if "args" in data and "offset_layers" in data["args"]:
            for i, offset_layer in enumerate(data["args"]["offset_layers"]):
                for j, offset in enumerate(offset_layer["offsets"]):
                    data["args"]["offset_layers"][i]["offsets"][j] = ast.literal_eval(offset)
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
    

    




