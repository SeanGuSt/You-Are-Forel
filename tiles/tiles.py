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
    image_path = None
    image = None
    combat_map = None
    color = (0, 0, 255)
    screen_x:int = 0
    screen_y:int = 0
    def calc_screen_pos(self, map_x, map_y, pixel_offset_x, pixel_offset_y):
        self.screen_x = map_x * TILE_WIDTH - pixel_offset_x
        self.screen_y = map_y * TILE_HEIGHT - pixel_offset_y

    def draw(self, surface, show_grid=False):
        if self.image:
            surface.blit(self.image, (self.screen_x, self.screen_y))
        else:
            print(self.screen_x, self.screen_y)
            rect = pygame.Rect(self.screen_x, self.screen_y, TILE_WIDTH, TILE_HEIGHT)
            pygame.draw.rect(surface, self.color, rect)
            if show_grid:
                pygame.draw.rect(surface, BLACK, rect, 1)
    def __post_init__(self):
        # Load image if path is provided
        self.name = self.__class__.__name__.lower()
        if self.image_path and os.path.exists(self.image_path):
            try:
                self.image = image_load(self.image_path)
            except:
                self.image = None

    def can_pass_thru(self):
        return self.is_passable
    
    


    