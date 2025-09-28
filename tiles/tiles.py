import json, os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pygame
from constants import TILE_HEIGHT, TILE_WIDTH, BLACK
from pygame.image import load as image_load
@dataclass
class Tile:
    is_passable = True
    can_see_thru = True
    name: str = ""
    step_sound = ""
    level = 0
    image_path = None
    image = None
    combat_map = None
    color = (0, 0, 255)
    screen_x:int = 0
    screen_y:int = 0
    args: Dict = None
    def calc_screen_pos(self, map_x, map_y, pixel_offset_x, pixel_offset_y):
        self.screen_x = map_x * TILE_WIDTH - pixel_offset_x
        self.screen_y = map_y * TILE_HEIGHT - pixel_offset_y
        
    def __post_init__(self):
        # Load image if path is provided
        merged_args = self.default_args()
        user_args = self.args
        if user_args:
            merged_args = {**merged_args, **user_args}
        self.name = self.__class__.__name__.lower()
        if self.image_path and os.path.exists(self.image_path):
            try:
                self.image = image_load(self.image_path)
            except:
                self.image = None

    def can_pass_thru(self, from_tile: "Tile" = None):
        if not self.is_passable:
            return False
        #If walking from offscreen, always allowed if passable
        if not from_tile:
            return True
        # Same level movement is always allowed if passable
        if self.level == from_tile.level:
            return True

        # Special stairs case
        if isinstance(self, StairsLevelAdjust) and abs(self.level - from_tile.level) == 1:
            return True

        return False
    
    @staticmethod
    def default_args() -> dict:
        return {}
    
class StairsLevelAdjust(Tile):   
    pass


    