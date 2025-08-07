from enum import Enum
from dataclasses import dataclass, field
from constants import VirtueType, OverusePenalty
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import pygame
if TYPE_CHECKING:
    from objects.characters import Character
    from magic import Spell
    from ultimalike import GameEngine

@dataclass
class Virtue:
    level: int = 1
    exp: int = 0
    overuse_points: int = 0
    base_threshold: int = 1
    threshold_per_level: int = 2
    penalty_type: OverusePenalty = OverusePenalty.STAT_REDUCTION
    penalty_value: int = 2
    nonuse_cooldown: int = 1
    
    def get_threshold(self) -> int:
        """Calculate total overuse threshold including level bonus"""
        return self.base_threshold + (self.level - 1) * self.threshold_per_level

@dataclass
class ActivePenalty:
    penalty_type: OverusePenalty
    virtue: VirtueType
    value: int
    description: str

class VirtueManager:
    """Manages magic classes, overuse points, and penalties for a character"""
    """If these ever become undesirable, simply set the overuse_cost and level of each spell to 0"""
    
    def __init__(self):
        self.virtues: Dict[VirtueType, Virtue] = {}
        self.active_penalties: List[ActivePenalty] = []
        self.equipment_threshold_bonus: int = 0
        
        # Initialize default magic classes
        self.load_virtues()
    
    def load_virtues(self):
        """Initialize all magic classes with default values"""
        penalty_mappings = {
            VirtueType.FIRE: (OverusePenalty.HP_DAMAGE, 3),
            VirtueType.ICE: (OverusePenalty.MOVEMENT_REDUCTION, 1),
            VirtueType.LIGHTNING: (OverusePenalty.ACCURACY_REDUCTION, 10),
            VirtueType.EARTH: (OverusePenalty.STAT_REDUCTION, 2),
            VirtueType.WATER: (OverusePenalty.SPELL_FAILURE, 25),
            VirtueType.WIND: (OverusePenalty.HP_DAMAGE, 5),
            VirtueType.LAVA: (OverusePenalty.STAT_REDUCTION, 2),
            VirtueType.NATURE: (OverusePenalty.STAT_REDUCTION, 1),
        }
        
        for virtue in VirtueType:
            penalty_type, penalty_value = penalty_mappings.get(virtue, (OverusePenalty.STAT_REDUCTION, 2))
            self.virtues[virtue] = Virtue(
                penalty_type=penalty_type,
                penalty_value=penalty_value
            )
    
    def get_virtue_level(self, virtue: VirtueType) -> int:
        """Get the level of a specific magic class"""
        return self.virtues[virtue].level
    
    def set_virtue_level(self, virtue: VirtueType, level: int, is_delta: bool = False):
        """Set the level of a specific magic class"""
        if virtue in self.virtues:
            if is_delta:
                level += self.virtues[virtue].level
            self.virtues[virtue].level = max(1, level)
    
    def get_overuse_threshold(self, virtue: VirtueType) -> int:
        """Get total overuse threshold including equipment bonuses"""
        base_threshold = self.virtues[virtue].get_threshold()
        return base_threshold + self.equipment_threshold_bonus
    
    def add_overuse_points(self, virtue: VirtueType, points: int) -> bool:
        """Add overuse points and return True if threshold exceeded"""
        if virtue not in self.virtues:
            return False
        
        virtue_data = self.virtues[virtue]
        virtue_data.overuse_points += points
        
        threshold = self.get_overuse_threshold(virtue)
        return virtue_data.overuse_points > threshold
    
    def _get_spell_failure_chance(self, virtue: VirtueType) -> int:
        """Get spell failure chance from active penalties"""
        for penalty in self.active_penalties:
            if (penalty.virtue == virtue and 
                penalty.penalty_type == OverusePenalty.SPELL_FAILURE):
                return penalty.value
        return 0
    
    def apply_turn_end_penalties(self, character: 'Character') -> List[str]:
        """Apply penalties for overused magic classes at turn end"""
        messages = []
        for virtue, magic_data in self.virtues.items():
            if virtue != character.virtue_used_this_turn:
                magic_data.overuse_points = max(0, magic_data.overuse_points- magic_data.nonuse_cooldown)
            threshold = self.get_overuse_threshold(virtue)
            
            if magic_data.overuse_points > threshold:
                # Check if penalty already active
                if not self._has_active_penalty(virtue, magic_data.penalty_type):
                    penalty = ActivePenalty(
                        penalty_type=magic_data.penalty_type,
                        virtue=virtue,
                        value=magic_data.penalty_value,
                        description=self._get_penalty_description(virtue, magic_data.penalty_type)
                    )
                    
                    self.active_penalties.append(penalty)
                    messages.append(f"Overuse penalty applied: {penalty.description}")
                for penalty in self.active_penalties:
                    if penalty.virtue == virtue:
                        self._apply_penalty_effect(penalty, character)
            else:
                for penalty in self.active_penalties:
                    if penalty.virtue == virtue:
                        self.active_penalties.remove(penalty)
                        messages.append(f"No longer experiencing {penalty.penalty_type.value}")
                        del penalty
                            
        character.virtue_used_this_turn = None
        return messages
    
    def _has_active_penalty(self, virtue: VirtueType, penalty_type: OverusePenalty) -> bool:
        """Check if a penalty is already active for a magic class"""
        return any(p.virtue == virtue and p.penalty_type == penalty_type 
                  for p in self.active_penalties)
    
    def _get_penalty_description(self, virtue: VirtueType, penalty_type: OverusePenalty) -> str:
        """Get description for penalty type"""
        descriptions = {
            OverusePenalty.STAT_REDUCTION: f"{virtue.value} overuse reduces stats",
            OverusePenalty.HP_DAMAGE: f"{virtue.value} overuse causes damage",
            OverusePenalty.ACCURACY_REDUCTION: f"{virtue.value} overuse reduces accuracy",
            OverusePenalty.SPELL_FAILURE: f"{virtue.value} spells may fail",
            OverusePenalty.MOVEMENT_REDUCTION: f"{virtue.value} overuse slows movement",
        }
        return descriptions.get(penalty_type, f"{virtue.value} overuse penalty")
    
    def _apply_penalty_effect(self, penalty: ActivePenalty, character: 'Character'):
        """Apply the immediate effect of a penalty"""
        if penalty.penalty_type == OverusePenalty.STAT_REDUCTION:
            # Reduce primary stat based on magic class
            if penalty.virtue in [VirtueType.FIRE, VirtueType.EARTH]:
                character.strength_delta -= penalty.value
            elif penalty.virtue in [VirtueType.ICE, VirtueType.LIGHTNING]:
                character.dexterity_delta -= penalty.value
            else:
                character.faith_delta -= penalty.value
        
        elif penalty.penalty_type == OverusePenalty.HP_DAMAGE:
            character.hp = max(1, character.hp - penalty.value)
    
    def process_turn_end(self, character: 'Character') -> List[str]:
        """Process all turn-end effects: apply new penalties and tick existing ones"""
        
        # Apply new penalties
        new_penalty_messages = self.apply_turn_end_penalties(character)
        for message in new_penalty_messages:
            character.engine.combat_manager.append_to_combat_log(message)
        
        return new_penalty_messages
    
    def _remove_penalty_effect(self, penalty: ActivePenalty, character: 'Character'):
        """Remove the effect of an expired penalty"""
        if penalty.penalty_type == OverusePenalty.STAT_REDUCTION:
            # Restore stats
            if penalty.virtue in [VirtueType.FIRE, VirtueType.EARTH]:
                character.strength_delta += penalty.value
            elif penalty.virtue in [VirtueType.ICE, VirtueType.LIGHTNING]:
                character.dexterity_delta += penalty.value
            else:
                character.faith_delta += penalty.value
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get current status information for UI display"""
        status = {
            'virtues': {},
            'active_penalties': [],
            'equipment_bonus': self.equipment_threshold_bonus
        }
        
        for virtue, data in self.virtues.items():
            status['virtues'][virtue.value] = {
                'level': data.level,
                'overuse_points': data.overuse_points,
                'threshold': self.get_overuse_threshold(virtue),
                'over_threshold': data.overuse_points > self.get_overuse_threshold(virtue)
            }
        
        for penalty in self.active_penalties:
            status['active_penalties'].append({
                'virtue': penalty.virtue.value,
                'type': penalty.penalty_type.value,
                'remaining_turns': penalty.remaining_turns,
                'description': penalty.description
            })
        
        return status