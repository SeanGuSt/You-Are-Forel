from constants import VirtueType, OverusePenalty
from typing import Dict, List, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from objects.characters import Character


class VirtueManager:
    """Simplified manager for virtue overuse and penalties."""

    penalty_mappings = {
        VirtueType.FIRE:      (OverusePenalty.HP_DAMAGE, 3),
        VirtueType.ICE:       (OverusePenalty.MOVEMENT_REDUCTION, 1),
        VirtueType.LIGHTNING: (OverusePenalty.ACCURACY_REDUCTION, 10),
        VirtueType.EARTH:     (OverusePenalty.CONTROL_RESTRICTION, "movement"),
        VirtueType.WATER:     (OverusePenalty.SPELL_FAILURE, 25),
        VirtueType.AIR:       (OverusePenalty.HP_DAMAGE, 5),
        VirtueType.MAGMA:     (OverusePenalty.STAT_REDUCTION, 2),
        VirtueType.NATURE:    (OverusePenalty.STAT_REDUCTION, 1),
    }

    def __init__(self):
        # virtues: { VirtueType: dict of stats }
        self.virtues: Dict[VirtueType, Dict[str, Any]] = {
            v: dict(
                level=1,
                overuse=0,
                base_threshold=1,
                threshold_per_level=2,
                penalty=self.penalty_mappings.get(v, (OverusePenalty.STAT_REDUCTION, 2))
            )
            for v in VirtueType
        }
        self.active_penalties: List[Dict[str, Any]] = []
        self.equipment_threshold_bonus = 0

    # --- Core getters/setters ---
    def get_level(self, virtue: VirtueType) -> int:
        return self.virtues[virtue]["level"]

    def set_level(self, virtue: VirtueType, level: int, delta: bool = False):
        if delta:
            level += self.virtues[virtue]["level"]
        self.virtues[virtue]["level"] = max(1, level)

    def get_threshold(self, virtue: str | VirtueType) -> int:
        if type(virtue) == str:
            virtue = VirtueType(virtue)
        v = self.virtues[virtue]
        return v["base_threshold"] + (v["level"] - 1) * v["threshold_per_level"] + self.equipment_threshold_bonus

    def add_overuse(self, virtue: VirtueType, points: int) -> bool:
        v = self.virtues[virtue]
        v["overuse"] += points
        return v["overuse"] > self.get_threshold(virtue)

    # --- Turn handling ---
    def process_turn_end(self, character: "Character") -> List[str]:
        messages = []
        for virtue, data in self.virtues.items():
            # reduce overuse if not used
            if virtue != character.virtue_used_this_turn:
                data["overuse"] = max(0, data["overuse"] - 1)

            threshold = self.get_threshold(virtue)
            penalty_type, penalty_value = data["penalty"]

            if data["overuse"] > threshold:
                # add penalty if not already active
                if not any(p["virtue"] == virtue for p in self.active_penalties):
                    desc = f"{virtue.value} overuse: {penalty_type.value}"
                    penalty = dict(virtue=virtue, type=penalty_type, value=penalty_value, description=desc)
                    self.active_penalties.append(penalty)
                    messages.append(f"Overuse penalty applied: {desc}")
                # apply effect
                self._apply_penalty(penalty_type, virtue, penalty_value, character)
            else:
                # remove penalties if below threshold
                to_remove = [p for p in self.active_penalties if p["virtue"] == virtue]
                for p in to_remove:
                    self._remove_penalty(p, character)
                    self.active_penalties.remove(p)
                    messages.append(f"No longer experiencing {p['type'].value}")

        character.virtue_used_this_turn = None
        return messages

    # --- Penalty effects ---
    def _apply_penalty(self, ptype, virtue, value, char):
        if ptype == OverusePenalty.STAT_REDUCTION:
            if virtue in [VirtueType.FIRE, VirtueType.EARTH]:
                char.strength_delta -= value
            elif virtue in [VirtueType.ICE, VirtueType.LIGHTNING]:
                char.dexterity_delta -= value
            else:
                char.faith_delta -= value
        elif ptype == OverusePenalty.HP_DAMAGE:
            char.hp = max(1, char.hp - value)

    def _remove_penalty(self, penalty, char):
        if penalty["type"] == OverusePenalty.STAT_REDUCTION:
            v = penalty["virtue"]
            if v in [VirtueType.FIRE, VirtueType.EARTH]:
                char.strength_delta += penalty["value"]
            elif v in [VirtueType.ICE, VirtueType.LIGHTNING]:
                char.dexterity_delta += penalty["value"]
            else:
                char.faith_delta += penalty["value"]

    # --- UI helper ---
    def get_status_info(self) -> Dict[str, Any]:
        return dict(
            virtues={
                v.value: dict(
                    level=data["level"],
                    overuse=data["overuse"],
                    threshold=self.get_threshold(v),
                    over_threshold=data["overuse"] > self.get_threshold(v),
                )
                for v, data in self.virtues.items()
            },
            active_penalties=self.active_penalties,
            equipment_bonus=self.equipment_threshold_bonus,
        )
    def is_overuse_blocking_movement(self, character: "Character") -> bool:
        """Check if the character's Earth virtue is over its threshold."""
        earth = self.virtues.get(VirtueType.EARTH)
        return earth and earth["overuse"] > self.get_threshold(VirtueType.EARTH)
    
    def overuse_accuracy_penalty(self, character: "Character"):
        water = self.virtues.get(VirtueType.WATER)
        if not water:
            return 0
        return max(0, water["overuse"] - self.get_threshold(VirtueType.EARTH))
