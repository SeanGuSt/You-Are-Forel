from typing import TYPE_CHECKING
import ast
from constants import *
import pygame
from Map_Editor.me_constants import EditState, SIDEBAR_SPACE_HEIGHT, SIDEBAR_SPACE_WIDTH
from Map_Editor.inputs.other_inputs import undo, redo
if TYPE_CHECKING:
    from Map_Editor.map_editor import MapEditor
def new_tile_input(self: 'MapEditor'):
    self.change_state(EditState.INPUT)
    self.input0 = ""

def new_object_input(self: 'MapEditor'):
    self.change_state(EditState.INPUT)
    self.input0 = ""

def recursive_dicts(big_dict, split_input: list[str], input1: str):
    if len(split_input) > 1:
        sp0 = split_input[0]
        sp1 = split_input[1:]
        if sp0 not in big_dict:
            big_dict[sp0] = {}
        recursive_dicts(big_dict[sp0], sp1, input1)
    elif "[" in input1 and "]" in input1:
        big_dict[split_input[0]] = ast.literal_eval(input1)
    else:
        try:
            big_dict[split_input[0]] = int(input1)
        except:
            big_dict[split_input[0]] = input1

def non_text_mode_inputs(self: 'MapEditor', event):
    mods = pygame.key.get_mods()
    match event.key:
        case pygame.K_TAB:
            if self.state == EditState.OBJECT:
                self.placing_mode = "tile"
                self.change_state(EditState.TILE)
            elif self.state == EditState.TILE:
                self.placing_mode = "object"
                self.change_state(EditState.OBJECT)
        case pygame.K_z:
            if mods & pygame.KMOD_CTRL:
                undo(self)
            else:
                new_tile_input(self)
        case pygame.K_y:
            if mods & pygame.KMOD_CTRL:
                redo(self)
        case pygame.K_RIGHT | pygame.K_LEFT:
            if self.state == EditState.TILE:
                self.tile_index = (self.tile_index + (1 if event.key == pygame.K_RIGHT else -1)) % len(self.char_list)
            else:
                self.object_index = (self.object_index + (1 if event.key == pygame.K_RIGHT else -1)) % len(self.object_types)
                self.selected_object_type = self.object_types[self.object_index]
        case pygame.K_w:
            if mods & pygame.KMOD_SHIFT: self.camera_y = max(self.camera_y - 1, 0)
            else: self.insert_row(above=True)
        case pygame.K_s:
            if mods & pygame.KMOD_SHIFT: self.camera_y = min(self.camera_y + 1, len(self.ascii_map) - self.VIEW_HEIGHT)
            else: self.insert_row(above=False)
        case pygame.K_a:
            if mods & pygame.KMOD_CTRL:
                full_map_mode = not full_map_mode
                if full_map_mode:
                    self.VIEW_WIDTH, self.VIEW_HEIGHT = min(27, len(self.ascii_map[0])), min(20, len(self.ascii_map))
                else:
                    self.VIEW_WIDTH, self.VIEW_HEIGHT = 13, 13
                self.camera_x, self.camera_y = 0, 0
                self.SCREEN_WIDTH, self.SCREEN_HEIGHT = TILE_WIDTH * self.VIEW_WIDTH + SIDEBAR_SPACE_WIDTH, TILE_HEIGHT * self.VIEW_HEIGHT + SIDEBAR_SPACE_HEIGHT  # Extra space for sidebar
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            elif mods & pygame.KMOD_SHIFT: self.camera_x = max(self.camera_x - 1, 0)
            else: self.insert_column(before=True)
        case pygame.K_d:
            if mods & pygame.KMOD_SHIFT: self.camera_x = min(self.camera_x + 1, len(self.ascii_map[0]) - self.VIEW_WIDTH)
            else: self.insert_column(before=False)
        case pygame.K_r:
            self.remove_row()
        case pygame.K_c:
            self.remove_column()