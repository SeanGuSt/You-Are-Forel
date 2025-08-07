from typing import TYPE_CHECKING
import ast
import pygame
from Map_Editor.me_constants import EditState
if TYPE_CHECKING:
    from Map_Editor.map_editor import MapEditor

def place_tile(self: 'MapEditor', event, tx, ty, keys_at_tile, mods):
    if self.state == EditState.INPUT or self.placing_mode=="object":
        return
    if mods & pygame.KMOD_SHIFT:
        self.paint_tiles.append((tx, ty))
        if len(self.paint_tiles) < 2:
            return
        tx0, ty0 = self.paint_tiles[0]
        tx1, ty1 = self.paint_tiles[1]
        tx_range = range(tx0, tx1 + 1) if tx0 <= tx1 else range(tx1, tx0 + 1)
        ty_range = range(ty0, ty1 + 1) if ty0 <= ty1 else range(ty1, ty0 + 1)
        for i in tx_range:
            for j in ty_range:
                if not self.tdb.tiles[self.tile_map[self.char_list[self.tile_index]]].is_passable:
                    keys_at_this_tile = [k for k,v in self.objects_data.items() if v["x"] == i and v["y"] == j]
                    if keys_at_this_tile:
                        continue
                self.ascii_map[j][i] = self.char_list[self.tile_index]
        self.paint_tiles = []
    if mods & pygame.KMOD_CTRL:
        self.tile_index = next((i for i, val in enumerate(self.char_list) if val == self.ascii_map[ty][tx]), None)
    if keys_at_tile and not self.tdb.tiles[self.tile_map[self.char_list[self.tile_index]]].is_passable:
        return
    self.ascii_map[ty][tx] = self.char_list[self.tile_index]
    self.mouse_dragging = True
    self.last_dragged_tiles.clear()
    self.last_dragged_tiles.add((tx, ty))
    
def place_or_move_object(self: 'MapEditor', event, tx, ty, keys_at_tile, mods):
    if self.state == EditState.INPUT or self.placing_mode == "tile":
        return
    if mods & pygame.KMOD_SHIFT:
        if not keys_at_tile:
            return
        self.dragged_object_key = keys_at_tile[0]
        self.ghost_object = self.objects_data[self.dragged_object_key].copy()
        return
    if not self.tdb.tiles[self.tile_map[self.ascii_map[ty][tx]]].is_passable:
        return
    not_already_occupied = True#To clarify: not already occupied means that the tile is not occupied by an object that is not passable, not necessarily that the tile is empty.
    if not self.odb.obj_templates[self.selected_object_type].is_passable:
        not_already_occupied = all(self.odb.obj_templates[self.objects_data[k]["object_type"]].is_passable() for k in keys_at_tile)
            
    if not_already_occupied:
        self.pending_object = {
            "object_type": self.selected_object_type,
            "x": tx,
            "y": ty,
            "args": {}
        }
        self.change_state(EditState.INPUT)
        self.input0 = "name"
        self.input_field = 1
    else:
        self.dragged_object_key = keys_at_tile[0]
        self.ghost_object = self.objects_data[self.dragged_object_key].copy()
        return
def drag_paint_tiles(self: 'MapEditor', tx, ty, keys_at_tile):
    if self.mouse_dragging and self.placing_mode == "tile":
        if (tx, ty) not in self.last_dragged_tiles:
            if keys_at_tile and not self.tdb.tiles[self.tile_map[self.char_list[self.tile_index]]].is_passable:
                return
            self.ascii_map[ty][tx] = self.char_list[self.tile_index]
            self.last_dragged_tiles.add((tx, ty))
def move_ghost(self: 'MapEditor', tx, ty, keys_at_tile):
    if self.dragged_object_key and self.ghost_object:
        if not self.odb.obj_templates[self.objects_data[self.dragged_object_key]["object_type"]].is_passable:
            if keys_at_tile or not self.tdb.tiles[self.tile_map[self.ascii_map[ty][tx]]].is_passable:
                    return
        self.ghost_object["x"] = tx
        self.ghost_object["y"] = ty