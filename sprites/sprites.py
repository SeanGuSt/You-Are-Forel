from constants import IMAGE_DIR, TILE_WIDTH, TILE_HEIGHT
from typing import TYPE_CHECKING
from constants import GRAY
from objects.object_templates import Node
import os
import pygame
if TYPE_CHECKING:
    from ultimalike import GameEngine
class SpriteDatabase:
    def __init__(self, engine: 'GameEngine'):
        self.sprites = {}
        self.icons = {}
        self.engine = engine
        self.color_variants = {}
        self.common_skin_colors = [
            (255, 220, 177),  # Light
            (241, 194, 125),  # Medium-light
            (224, 172, 105),  # Medium
            (198, 134, 66),   # Medium-dark
            (141, 85, 36),    # Dark
        ]
        self.load_from_files()

    def load_from_files(self):
        onlyfiles = [f for f in os.listdir(IMAGE_DIR) if os.path.isfile(os.path.join(IMAGE_DIR, f))]
        for file_name in onlyfiles:
            if file_name.endswith(".png"):
                sheet_name = file_name[:-4]
                self.sprites[sheet_name] = pygame.transform.scale_by(pygame.image.load(os.path.join(IMAGE_DIR, file_name)).convert_alpha(), 2)
                
                # Pre-generate color variants for people sprites
                if sheet_name.startswith("Generic People"):
                    self.color_variants[sheet_name] = {}
                    for skin_color in self.common_skin_colors:
                        variant_sheet = replace_color_threshold(self.sprites[sheet_name].copy(), GRAY, skin_color)
                        self.color_variants[sheet_name][skin_color] = variant_sheet
                
    
    def get_sprite(self, node: Node, new_row: int = None, new_col: int = None, is_delta: bool = False):
        if not "spritesheet" in node.args:
            return
        sheet_name = node.args["spritesheet"][0]
        sheet = self.sprites.get(sheet_name)
        if not sheet:
            return
        if not new_row is None:
            if is_delta:
                node.args["spritesheet"][1] += new_row
            else:
                node.args["spritesheet"][1] = new_row
        if not new_col is None:
            if is_delta:
                node.args["spritesheet"][2] += new_col
            else:
                node.args["spritesheet"][2] = new_col
        sprite_row = node.args["spritesheet"][1]
        sprite_col = node.args["spritesheet"][2]
        
        # Use pre-generated color variant if available
        if sheet_name.startswith("Generic People") and node.skin_color in self.color_variants.get(sheet_name, {}):
            sheet = self.color_variants[sheet_name][node.skin_color]
        
            node.image = sheet.subsurface(pygame.Rect(
                sprite_col * TILE_WIDTH, 
                sprite_row * TILE_HEIGHT, 
                TILE_WIDTH*node.width_in_tiles, 
                TILE_HEIGHT*node.height_in_tiles
            ))
        else:
            node.image = sheet.subsurface(pygame.Rect(sprite_col*TILE_WIDTH, sprite_row*TILE_HEIGHT, TILE_WIDTH*node.width_in_tiles, TILE_HEIGHT*node.height_in_tiles))

def replace_color_threshold(surface, old_color, new_color, threshold=0):
        # Create a mask for the color to replace
        """Replace only gray colors in a specific range, preserving outlines and transparency"""
        surface = surface.convert_alpha()
        new_surface = surface.copy()
        
        # Create a pixel array for faster processing
        pixel_array = pygame.PixelArray(new_surface)
        original_array = pygame.PixelArray(surface)
        
        width, height = surface.get_size()
        
        for x in range(width):
            for y in range(height):
                # Get the original pixel color
                pixel_color = surface.unmap_rgb(original_array[x, y])
                
                # Skip transparent pixels
                if len(pixel_color) > 3 and pixel_color[3] == 0:
                    continue
                
                # Check if pixel is in the gray range we want to replace
                if pixel_color[:3] == old_color:
                    
                    # Replace with skin color
                    if len(pixel_color) > 3 and len(new_color) < 4:  # Has alpha
                        new_color = (*new_color, pixel_color[3])
                    else:
                        new_color = new_color
                    pixel_array[x, y] = new_surface.map_rgb(new_color)
        
        # Clean up
        del pixel_array
        del original_array
        
        return new_surface
    