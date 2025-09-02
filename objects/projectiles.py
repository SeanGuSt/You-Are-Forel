import os
from dataclasses import dataclass, asdict, fields, MISSING
import random
import json, pygame
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from tiles.tiles import Tile
from tiles.tile_database import TileDatabase
from constants import *
import copy
from objects.object_templates import Node, Monster, CombatStatsMixin, Spawner, register_node_type
if TYPE_CHECKING:
    from objects.characters import Character
    from ultimalike import GameEngine
    from objects.map_objects import Map

@register_node_type("battleprojectile")
@dataclass
class BattleProjectile(Node):
    master: Node = None
    @classmethod
    def from_dict(cls, data: dict, engine: 'GameEngine') -> Node:
        self = super().from_dict(data, engine)
        print(f"Debug: {self.args["delay"]}")
        if self.args["delay"] == 0:
            self.state = ObjectState.ATTACK_MELEE
            self.engine.event_manager.timer_manager.start_timer(f"{self.name}_attack", 1000)
        else:
            self.state = ObjectState.SLEEP
            self.engine.event_manager.timer_manager.start_timer(f"{self.name}_wakeup", self.args["delay"])
        return self
    def default_args():
        return {"spritesheet" : ["TestRaisingProjectile", 0, 0]}
    def update(self):
        super().update()
        timer_manager = self.engine.event_manager.timer_manager
        match self.state:
            case ObjectState.SLEEP:
                if timer_manager.get_progress(f"{self.name}_wakeup") >= 1.0:
                    print(f"Debug: {self.name} woke up")
                    self.state = ObjectState.WIGGLE
                    timer_manager.start_timer(f"{self.name}_attack", 1000)
            case ObjectState.WIGGLE:
                num_frames = 7
                frame = int(num_frames*timer_manager.get_progress(f"{self.name}_attack"))
                if frame >= num_frames:
                    timer_manager.start_timer(f"{self.name}_attack", 125)
                    self.engine.sprite_db.get_sprite(self, 1, 0)
                    self.state = ObjectState.ATTACK_MELEE
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = 1 + frame)
            case ObjectState.ATTACK_MELEE:
                num_frames = 5
                frame = int(num_frames*timer_manager.get_progress(f"{self.name}_attack"))
                if frame >= num_frames:
                    for obj in self.engine.current_map.get_objects_at(self.position):
                        if obj != self and obj.__is__(CombatStatsMixin):
                            obj.hp -= 5
                            obj.attacked(self.master, 5)
                    timer_manager.start_timer(f"{self.name}_dying", 350)
                    self.state = ObjectState.DYING
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = frame)
            case ObjectState.DYING:
                if timer_manager.get_progress(f"{self.name}_dying") >= 1.0:
                    self.state = ObjectState.DEATH
            case ObjectState.DEATH:
                self.destroy()

