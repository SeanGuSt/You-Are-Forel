from dataclasses import dataclass, asdict, field, MISSING
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import pygame
from constants import *
from objects.object_templates import Node, CombatStatsMixin, Monster, MapObject, Teleporter, Spawner, Chest, Missile, NPC, NODE_REGISTRY, register_node_type
if TYPE_CHECKING:
    from objects.characters import Character
    from ultimalike import GameEngine
@register_node_type("bedbasic")
class BedBasic(MapObject):
    is_passable = True

@register_node_type("bedroyal")
class BedRoyal(BedBasic):
    color = ROYAL_BLUE

@register_node_type("doorbasic")
class DoorBasic(MapObject):
    color = BROWN
    is_passable = True

@register_node_type("doorlocked")
class DoorLocked(DoorBasic):
    is_passable = False

@register_node_type("elevatorhelper")
class ElevatorHelper(NPC):
    color = DARK_GREEN

@register_node_type("elevatorteleporter")
class ElevatorTeleporter(Teleporter):
    activate_by_stepping_on = False

@register_node_type("pillar")
class Pillar(MapObject):
    is_passabe = False
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 0, 0]}
    
@register_node_type("archerytarget")
class ArcheryTarget(MapObject):
    is_passable = False
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 1, 2]}
    
@register_node_type("arrowmissile")
class ArrowMissile(Missile):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 1, 0]}
    
@register_node_type("arrowspawner")
@dataclass
class ArrowSpawner(Spawner):
    pass

@register_node_type("npccrossbower")
@dataclass
class NPCCrossbower(ArrowSpawner):
    def execute_repeating_action(self, action):
        if self.state == ObjectState.STAND:
            for obj in self.map.get_objects_at(self.position):
                if "shooting_range" in obj.name:
                    arrow = self.spawn_object_at_position("arrowmissile")
                    if arrow.__is__(Missile):
                        shooting_direction = action.direction
                        arrow.move_direction = shooting_direction
                        arrow.state = ObjectState.KEEP_MOVING
                        arrow.move_interval = 0.25
                        if arrow.image:
                            match shooting_direction:
                                case Direction.NORTH:
                                    arrow.image = pygame.transform.rotate(arrow.image, 270)
                                case Direction.SOUTH:
                                    arrow.image = pygame.transform.rotate(arrow.image, 90)
                                case Direction.WEST:
                                    arrow.image = pygame.transform.rotate(arrow.image, 180)
                        arrow.move_one_step()
    @staticmethod
    def from_dict(data: dict, engine: 'GameEngine') -> 'NPCCrossbower':
        data["move_interval"] = 1.0
        new_obj = super(NPCCrossbower, NPCCrossbower).from_dict(data, engine)
        return new_obj
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Generic People", 0, 2]}
    
@register_node_type("npcsoldier")
class NPCSoldier(NPC):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Generic People", 0, 4]}
    
@register_node_type("npcguard")
class NPCGuard(NPC):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Generic People", 0, 3]}

@register_node_type("npcstudent")
class NPCStudent(NPC):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Generic People", 0, 1]}

@register_node_type("book")  
class Book(MapObject):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 0, 6]}
    
@register_node_type("bookclosed")
class BookClosed(Book):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 0, 5]}
    
@register_node_type("bookfake")  
class BookFake(Book):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 0, 7]}
    
@register_node_type("corpse")
class Corpse(MapObject):
    pass

@register_node_type("burntcorpse")
class BurntCorpse(Corpse):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 1, 5]}
    
@register_node_type("monsterguardrookie")
class MonsterGuardRookie(Monster):
    power = 3
    def my_battle_tactics(self):
        if not self.current_target:
            self.current_target = self.engine.party.get_leader()
        
        dist = self.subtract_tuples(self.current_target.position, self.position)
        dx, dy = self.get_sign(dist)
        
        # 1. Attack if adjacent (orthogonally adjacent only)
        if dist in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            self.attack(self.current_target)
        
        # 2. If not in same column, move toward target's column
        elif dist[0]:  # Not in same column
            new_pos = self.add_tuples(self.position, (dx, 0))
            if self.map.is_passable(new_pos):
                self.old_position = self.position
                self.position = new_pos
                self.last_move_direction = Direction((dx, 0))
        
        # 3. If in same column, move toward target's row
        elif not dist[0]:  # In same column
            new_pos = self.add_tuples(self.position, (0, dy))
            if self.map.is_passable(new_pos):
                self.old_position = self.position
                self.position = new_pos
                self.last_move_direction = Direction((0, dy))
        
        # 4. If we reach here, we couldn't move - skip turn
        # (No action needed, turn ends naturally)
    
    def attacked(self, attacker, damage):
        self.current_target = attacker
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Generic People", 0, 3]}

@register_node_type("monstereventtrigger")
class MonsterEventTrigger(Monster):
    @classmethod
    def from_dict(cls, data, engine):
        cls = super().from_dict(data, engine)
        cls.round_counter: int = 0
        cls.turn_counter: int = 0
        return cls

    def my_battle_tactics(self):
        self.round_counter += 1
        print(f"round counter is now {self.round_counter} out of {self.args.get("round_timer", 9999)}")
        if self.round_counter >= self.args.get("round_timer", 9999):
            self.engine.combat_manager.exit_combat_mode()
            self.engine.change_state(GameState.EVENT)

@register_node_type("animatedobject")
class AnimatedObject(MapObject):
    frames_since_last_change: int = 0
    frame_rule: int = 0
    current_col = 0
    min_col = 0
    max_col = 7
    @classmethod
    def from_dict(cls, data, engine):
        cls = super().from_dict(data, engine)
        cls.current_col = cls.min_col
        return cls
    def update(self):
        self.frames_since_last_change += 1
        if self.frames_since_last_change >= self.frame_rule:
            self.frames_since_last_change = 0
            self.current_col += 1
            if self.current_col > self.max_col:
                self.current_col = self.min_col
            self.engine.sprite_db.get_sprite(self, new_col=self.current_col)

@register_node_type("animatedburningman")
class AnimatedBurningMan(AnimatedObject):
    frame_rule = 45
    min_col = 3
    max_col = 4
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 1, 3]}
