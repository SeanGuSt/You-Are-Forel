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
    is_passable: bool = True

@register_node_type("bedroyal")
class BedRoyal(BedBasic):
    color = ROYAL_BLUE

@register_node_type("haremwardrobe")
class HaremWardrobe(Chest):
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Harem Wardrobe", 0, 0]}

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

@register_node_type("merchant")
class Merchant(NPC):
    color = DARK_BLUE

@register_node_type("elevatorteleporter")
class ElevatorTeleporter(Teleporter):
    activate_by_stepping_on = False

@register_node_type("pillar")
class Pillar(MapObject):
    is_passabe: bool = False
    can_see_thru = False
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 0, 0]}
    
@register_node_type("archerytarget")
class ArcheryTarget(MapObject):
    is_passable: bool = False
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
class ArrowSpawner(Spawner, NPC):
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
    
@register_node_type("grouppassable")
class GroupPassable(MapObject):
    is_passable = True

@register_node_type("book")  
class Book(MapObject):
    is_passable = False
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 0, 6]}
    
@register_node_type("bookpillar")
class BookPillar(Book):
    pass
    
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

@register_node_type("animatedobject")
class AnimatedObject(MapObject):
    frames_since_last_change: int = 0
    frame_rule = 0
    loop = True
    current_row = 0
    min_row = 0
    max_row = 7
    current_col = 0
    min_col = 0
    max_col = 7
    @classmethod
    def from_dict(cls, data, engine):
        cls = super().from_dict(data, engine)
        cls.current_col = cls.min_col
        cls.current_row = cls.min_row
        return cls
    def update(self, **args):
        super().update(**args)
        if self.frames_since_last_change < 0:
            return
        self.frames_since_last_change += 1
        if self.frames_since_last_change >= self.frame_rule:
            self.frames_since_last_change = 0
            self.current_col += self.width_in_tiles
            if self.current_col > self.max_col:
                self.current_col = self.min_col
                self.current_row += self.height_in_tiles
                if self.current_row > self.max_row:
                    self.current_row = self.min_row
                    if not self.loop:
                        self.frames_since_last_change = -1
                        return
            print(self.current_row, self.current_col)
            self.engine.sprite_db.get_sprite(self, new_row=self.current_row, new_col=self.current_col)

@register_node_type("animatedburningman")
class AnimatedBurningMan(AnimatedObject):
    frame_rule = 45
    min_row = 1
    max_row = 1
    min_col = 3
    max_col = 4
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Static Objects", 1, 3]}

@register_node_type("animatedforeleratonhug")
class AnimatedForelEratonHug(AnimatedObject):
    frame_rule = 8
    width_in_tiles = 2
    loop = False
    max_row = 1
    max_col = 7
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Forel Eraton Hug", 0, 0]}
    
@register_node_type("imedes_renald")
class Imedes_Renald(MapObject):
    width_in_tiles = 3
    height_in_tiles = 4
    burn_timer: int = 0
    def update(self, **args):
        super().update(**args)
        match self.state:
            case ObjectState.HEAD_TILT:
                num_frames = 3
                progress = self.engine.event_manager.timer_manager.get_progress(f"event_play_{self.name}")
                frame = int(num_frames*progress)
                self.engine.sprite_db.get_sprite(self, new_col = frame)
            case ObjectState.IMEDES_AMBUSH:
                num_frames = 15
                progress = self.engine.event_manager.timer_manager.get_progress(f"event_play_{self.name}")
                row = 1
                frame = int(num_frames*progress)
                if frame >= 8:
                    row = 2
                    frame -= 8
                
                self.engine.sprite_db.get_sprite(self, row, frame)
            case ObjectState.BURNING:
                num_frames = 2
                self.burn_timer += 1
                if self.burn_timer >= 60:
                    self.burn_timer = 0
                burn_frame = int(num_frames*self.burn_timer/60)
                self.engine.sprite_db.get_sprite(self, 3, burn_frame)
            case ObjectState.WALK:
                num_frames = 3
                progress = self.engine.event_manager.timer_manager.get_progress(f"event_play_{self.name}")
                frame = int(num_frames*progress)
                self.engine.sprite_db.get_sprite(self, 3, new_col = 2 + frame)
            case ObjectState.SLEEP:
                self.engine.sprite_db.get_sprite(self, 3, 5)
                

    def default_args():
        return {"spritesheet" : ["Imedes Renald Chokehold", 0, 0]}
