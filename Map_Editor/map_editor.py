import pygame
import json
import ast
import os
import copy
from objects.map_objects import MapObjectDatabase
from tiles.tile_database import TileDatabase
from Map_Editor.me_constants import *
from ultimalike import GameEngine
from Map_Editor.me_renderer import Renderer

from Map_Editor.inputs.new_things_inputs import non_text_mode_inputs
from Map_Editor.inputs.other_inputs import record_additions
from Map_Editor.inputs.text_inputs import input_new_tile_inputs, input_new_objects_inputs
from Map_Editor.inputs.mouse_inputs import place_or_move_object, place_tile, move_ghost, drag_paint_tiles

pygame.init()
map_name = "Kesvelt_Phitemos_Chambers"
FONT = pygame.font.SysFont(None, 18)
pygame.key.set_repeat(600, 200)

class MapEditor:
    def __init__(self, map_name: str):
        # Pygame setup
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"Styled Map Editor: {map_name}")
        self.clock = pygame.time.Clock()

        self.map_name = map_name
        # Add undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []

        #Databases
        self.odb = MapObjectDatabase(GameEngine)
        self.tdb = TileDatabase()
        self.renderer = Renderer(self, FONT)

        #file directories
        self.map_folder = ""
        self.ascii_path = ""
        self.tiles_path = ""
        self.objects_path = ""
        self.placing_mode = "tile"

        #file outputs
        self.ascii_map = [[]]
        self.tile_map = {}
        self.char_list = []
        self.objects_data = {}
        self.object_types = list(self.odb.obj_templates.keys())
        self.object_types.sort()
        self.tile_index = 0
        self.object_index = 0
        self.selected_object_type = self.object_types[self.object_index]

        self.SCREEN_HEIGHT = SCREEN_HEIGHT
        self.SCREEN_WIDTH = SCREEN_WIDTH
        self.VIEW_HEIGHT = VIEW_HEIGHT
        self.VIEW_WIDTH = VIEW_WIDTH

        self.camera_x = 0
        self.camera_y = 0

        self.state = EditState.TILE
        self.previous_state = None
        self.input_field = 0
        self.input0 = ""
        self.input1 = ""

        # Add popup input for object args
        self.arg_input_args = {}
        self.pending_object = None

        # Add a cursor toggle to blink
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_interval = 500  # ms
        # view the full map
        self.full_map_mode = False

        # Dragging support
        self.mouse_dragging = False
        self.last_dragged_tiles = set()
        self.dragged_object_key = None
        self.ghost_object = None
        self.paint_tiles = []


        self.open_map()

    def open_map(self):
        # File paths
        map_name = self.map_name
        map_folder = os.path.join(MAPS_DIR, map_name)
        self.ascii_path = os.path.join(map_folder, f"map_{map_name}.txt")
        self.tiles_path = os.path.join(map_folder, f"tiles_{map_name}.json")
        self.objects_path = os.path.join(map_folder, f"objs_{map_name}.json")
        
        self.map_folder = map_folder
        self.create_map_if_new()

        # Load data
        with open(self.ascii_path) as f:
            self.ascii_map = [list(line.strip()) for line in f.readlines()]

        with open(self.tiles_path) as f:
            self.tile_map = json.load(f)
        self.char_list = list(self.tile_map.keys())
        self.char_list.sort()

        with open(self.objects_path) as f:
            self.objects_data = json.load(f)

    def create_map_if_new(self):
        # Create files if not found
        def ensure_file_exists(path, default):
            if not os.path.exists(path):    
                if not os.path.exists(self.map_folder):
                    os.makedirs(self.map_folder)
                with open(path, "w") as f:
                    if path.endswith(".json"):
                        if isinstance(default, dict):
                            json.dump(default, f, indent=2)
                    else:
                        f.write(default)

        ascii_default = "#" * VIEW_WIDTH + "\n" + ("#" + "_" * (VIEW_WIDTH - 2) + "#\n") * (VIEW_HEIGHT - 2) + "#" * VIEW_WIDTH + "\n"
        ensure_file_exists(self.ascii_path, ascii_default)
        tile_default = {"#" : "wall", "_" : "floor", "." : "grass", "~" : "sky"}
        ensure_file_exists(self.tiles_path, tile_default)
        obj_default = {"new_game_spawner" : {"object_type" : "node", "x" : 10, "y" : 10}}
        ensure_file_exists(self.objects_path, obj_default)
    
    def change_state(self, state: EditState):
        self.previous_state = self.state
        self.state = state

    def revert_state(self):
        self.change_state(self.previous_state)
    
    def render(self):
        self.renderer.draw_sidebar()
        self.renderer.render_map()
        self.renderer.render_objects()
        if self.state == EditState.INPUT:
            match self.previous_state:
                case EditState.TILE:
                    self.renderer.draw_input_box(self.input0, self.input1, "New Ascii:", "Tile name:")
                case EditState.OBJECT:
                    self.renderer.draw_input_box(self.input0, self.input1, "Key:", "Value:")
        else:
            tx, ty = self.pointer_is_on_map()
            self.renderer.draw_tooltips(tx, ty, self.camera_x, self.camera_y, self.objects_data)
            if self.ghost_object and self.state == EditState.OBJECT:
                self.renderer.draw_ghost_object(self.ghost_object, self.camera_x, self.camera_y)
                
            

    # Add the following utility functions above the main loop:
    def pointer_is_on_map(self):
        mx, my = pygame.mouse.get_pos()
        if mx > VIEW_WIDTH * TILE_WIDTH or my > VIEW_HEIGHT * TILE_HEIGHT:
            return -1, -1
        x, y = mx // TILE_WIDTH + self.camera_x, my // TILE_HEIGHT + self.camera_y
        return x, y
    
    def insert_row(self, above=True):
        x, y = self.pointer_is_on_map()
        if x < 0:
            return
        fill_char = self.char_list[0]
        new_row = [fill_char] * len(self.ascii_map[0])
        index = y if above else y + 1
        self.ascii_map.insert(index, new_row)
        for obj in self.objects_data.values():
            if obj['y'] >= index:
                obj['y'] += 1
        record_additions(self)
    
    def remove_row(self):
        x, y = self.pointer_is_on_map()
        if x < 0:
            return
        if 0 <= y < len(self.ascii_map):
            self.ascii_map.pop(y)
            to_delete = [k for k, v in self.objects_data.items() if v['y'] == y]
            for k in to_delete:
                del self.objects_data[k]
            for obj in self.objects_data.values():
                if obj['y'] > y:
                    obj['y'] -= 1
            record_additions(self)

    def insert_column(self, before=True):
        x, y = self.pointer_is_on_map()
        if x < 0:
            return
        fill_char = self.char_list[0]
        for row in self.ascii_map:
            index = x if before else x + 1
            row.insert(index, fill_char)
        for obj in self.objects_data.values():
            if obj['x'] >= index:
                obj['x'] += 1
        record_additions(self)

    def remove_column(self):
        x, y = self.pointer_is_on_map()
        if x < 0:
            return
        if 0 <= x < len(self.ascii_map[0]):
            for row in self.ascii_map:
                row.pop(x)
            to_delete = [k for k, v in self.objects_data.items() if v['x'] == x]
            for k in to_delete:
                del self.objects_data[k]
            for obj in self.objects_data.values():
                if obj['x'] > x:
                    obj['x'] -= 1
            record_additions(self)
    
    def handle_input(self):
        for event in pygame.event.get():
            match event.type:
                case pygame.QUIT:
                    return False
                case pygame.KEYDOWN:
                    match self.state:
                        case EditState.TILE | EditState.OBJECT:
                            if event.key == pygame.K_ESCAPE:
                                return False
                            non_text_mode_inputs(self, event)
                        case EditState.INPUT:
                            if self.placing_mode == "tile":
                                input_new_tile_inputs(self, event)
                            if self.placing_mode == "object":
                                input_new_objects_inputs(self, event)
                        
                case pygame.MOUSEBUTTONDOWN:
                    tx, ty = self.pointer_is_on_map()
                    mods = pygame.key.get_mods()
                    keys_at_tile = [k for k,v in self.objects_data.items() if v["x"] == tx and v["y"] == ty]
                    match event.button:
                        case 1:
                            if self.placing_mode == "tile":
                                place_tile(self, event, tx, ty, keys_at_tile, mods)
                            else:
                                place_or_move_object(self, event, tx, ty, keys_at_tile, mods)
                            record_additions(self)
                        case 3:
                            for k in keys_at_tile:
                                del self.objects_data[k]
                case pygame.MOUSEMOTION:
                    tx, ty = self.pointer_is_on_map()
                    keys_at_tile = [k for k,v in self.objects_data.items() if v["x"] == tx and v["y"] == ty and not self.odb.obj_templates[v["object_type"]].is_passable]
                    drag_paint_tiles(self, tx, ty, keys_at_tile)
                    move_ghost(self, tx, ty, keys_at_tile)
                case pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.dragged_object_key and self.ghost_object:
                            self.objects_data[self.dragged_object_key]["x"] = self.ghost_object["x"]
                            self.objects_data[self.dragged_object_key]["y"] = self.ghost_object["y"]
                        self.dragged_object_key = None
                        self.ghost_object = None
                        self.mouse_dragging = False
                        self.last_dragged_tiles.clear()
        return True


running = True
map_editor = MapEditor(map_name)
while running:
    # Timer update for cursor
    map_editor.cursor_timer += map_editor.clock.get_time()
    if map_editor.cursor_timer >= map_editor.cursor_interval:
        map_editor.cursor_visible = not map_editor.cursor_visible
        map_editor.cursor_timer = 0
    running = map_editor.handle_input()
    map_editor.render()

    pygame.display.flip()
    map_editor.clock.tick(30)

with open(map_editor.ascii_path, "w") as f:
    for row in map_editor.ascii_map:
        f.write("".join(row) + "\n")
with open(map_editor.objects_path, "w") as f:
    json.dump(map_editor.objects_data, f, indent=2)
with open(map_editor.tiles_path, "w") as f:
    json.dump(map_editor.tile_map, f, indent=2)

pygame.quit()