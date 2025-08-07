import json, os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pygame.image import load as image_load
@dataclass
class Tile:
    is_passable = True
    name: str = ""
    step_sound = ""
    image_path = None
    image = None
    combat_map = None
    color = (0, 0, 255)
    def __post_init__(self):
        # Load image if path is provided
        self.name = self.__class__.__name__.lower()
        if self.image_path and os.path.exists(self.image_path):
            try:
                self.image = image_load(self.image_path)
            except:
                self.image = None


    