import pygame
import json
import ast
import os
import copy
from objects.map_objects import MapObjectDatabase
from tiles.tile_database import TileDatabase
from Map_Editor.me_constants import *
from ultimalike import GameEngine

pygame.init()
FONT = pygame.font.SysFont("consolas", 18)
map_name = "town"#"Kesvelt_Ground"

# Add undo/redo stacks
undo_stack = []
redo_stack = []

# File paths
map_folder = os.path.join(MAPS_DIR, map_name)
ascii_path = os.path.join(map_folder, f"map_{map_name}.txt")
tiles_path = os.path.join(map_folder, f"tiles_{map_name}.json")
objects_path = os.path.join(map_folder, f"objs_{map_name}.json")

#Databases
odb = MapObjectDatabase(GameEngine)
tdb = TileDatabase()

# Create files if not found
def ensure_file_exists(path, default):
    if not os.path.exists(path):
        if not os.path.exists(map_folder):
            os.makedirs(map_folder)
        with open(path, "w") as f:
            if path.endswith(".json"):
                if isinstance(default, dict):
                    json.dump(default, f, indent=2)
            else:
                f.write(default)

ascii_default = "#" * VIEW_WIDTH + "\n" + ("#" + "_" * (VIEW_WIDTH - 2) + "#\n") * (VIEW_HEIGHT - 2) + "#" * VIEW_WIDTH + "\n"
ensure_file_exists(ascii_path, ascii_default)
ensure_file_exists(tiles_path, {"#" : "wall", "_" : "floor", "." : "grass"})
ensure_file_exists(objects_path, {})

# Load data
with open(ascii_path) as f:
    ascii_map = [list(line.strip()) for line in f.readlines()]

with open(tiles_path) as f:
    tile_map = json.load(f)
char_list = list(tile_map.keys())

objects_data = {}
if os.path.exists(objects_path):
    with open(objects_path) as f:
        objects_data = json.load(f)

# Pygame setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(f"Styled Map Editor: {map_name}")

# Track state
tile_index = 0
placing_mode = "tile"
object_types = list(odb.obj_templates.keys())
object_index = 0
selected_object_type = object_types[object_index]
# Track which field is active in input
input_field = 0
input_mode = False
input0 = ""
input1 = ""
# Add popup input for object args
arg_input_mode = False
arg_input_args = {}
arg_input_stage = 0
pending_object = None
# Add a cursor toggle to blink
cursor_visible = True
cursor_timer = 0
cursor_interval = 500  # ms
# view the full map
full_map_mode = False

# Dragging support
mouse_dragging = False
last_dragged_tiles = set()
dragged_object_key = None
ghost_object = None
paint_tiles = []

def draw_tooltip(name, obj_type, screen_x, screen_y):
    text = f"{name} ({obj_type})"
    surf = FONT.render(text, True, (255, 255, 255))
    bg = pygame.Surface((surf.get_width() + 6, surf.get_height() + 4))
    bg.fill((0, 0, 0))
    screen.blit(bg, (screen_x + 10, screen_y - 10))
    screen.blit(surf, (screen_x + 13, screen_y - 8))

camera_x = 0
camera_y = 0

clock = pygame.time.Clock()



def draw_sidebar():
    # UI Helpers
    sidebar_rect = pygame.Rect(SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH, 0, SIDEBAR_SPACE_WIDTH, SCREEN_HEIGHT)
    pygame.draw.rect(screen, (30, 30, 30), sidebar_rect)
    pygame.draw.line(screen, (100, 100, 100), (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH, 0), (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH, SCREEN_HEIGHT))
    title = FONT.render("Map Editor", True, (255, 255, 255))
    screen.blit(title, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 10))
    mode = FONT.render(f"Mode: {placing_mode}", True, (255, 255, 0))
    screen.blit(mode, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 40))
    if placing_mode == "tile":
        tile_ascii = char_list[tile_index]
        tile_text = FONT.render(f"Tile: '{tile_ascii}': {tile_map[tile_ascii]}", True, (255, 255, 255))
        screen.blit(tile_text, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 70))
    else:
        obj = object_types[object_index]
        obj_text = FONT.render(f"Object: {obj}", True, (255, 255, 255))
        screen.blit(obj_text, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 70))
    controls = [
        "[TAB] Toggle Mode",
        "[<]/[>] Cycle Tile/Object",
        "[z] Add Tile",
        "[WASD] Inser Row/Column at Cursor",
        "[r] Remove Row at Cursor",
        "[c] Remove Column at Cursor",
        "[Shift+WASD] Scroll Map",
        "[Click] Place",
        "[Shift+Click] Paint Area with Tile",
        "[Ctrl+Click] Cycle to Tile/Object",
        "[Right Click] Delete Object",
        "[Ctrl+z] Undo",
        "[Ctrl+y] Redo",
        "[Ctrl+a] Toggle Full Map",
        "[ESC] Exit"
    ]
    for i, line in enumerate(controls):
        label = FONT.render(line, True, (200, 200, 200))
        screen.blit(label, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 10, 120 + i * 25))

def draw_input_box():
    pygame.draw.rect(screen, (0, 0, 0), (100, 100, 400, 140))
    pygame.draw.rect(screen, (255, 255, 255), (100, 100, 400, 140), 2)
    label1 = FONT.render("New ASCII:", True, (255, 255, 255))
    label2 = FONT.render(input0, True, (0, 255, 0))
    label3 = FONT.render("Tile name:", True, (255, 255, 255))
    label4 = FONT.render(input1, True, (0, 255, 0))
    screen.blit(label1, (110, 110))
    screen.blit(label2, (110 + label1.get_width(), 110))
    screen.blit(label3, (110, 150))
    screen.blit(label4, (110 + label3.get_width(), 150))
    # Blinking cursor
    if cursor_visible:
        if input_field == 0:
            cursor_at = 110 + label1.get_width() + label2.get_width()
            pygame.draw.line(screen, (0, 255, 0), (cursor_at, 110), (cursor_at, 128), 2)
        else:
            cursor_at = 110 + label3.get_width() + label4.get_width()
            pygame.draw.line(screen, (0, 255, 0), (cursor_at, 150), (cursor_at, 168), 2)

def draw_arg_input_box():
    pygame.draw.rect(screen, (0, 0, 0), (100, 100, 420, 180))
    pygame.draw.rect(screen, (255, 255, 255), (100, 100, 420, 180), 2)
    label0 = FONT.render("Enter object args (key:value)", True, (255, 255, 255))
    label1 = FONT.render("Key:", True, (255, 255, 255))
    label2 = FONT.render(input0, True, (0, 255, 0))
    label3 = FONT.render("Value:", True, (255, 255, 255))
    label4 = FONT.render(input1, True, (0, 255, 0))
    screen.blit(label0, (110, 110))
    screen.blit(label1, (110, 140))
    screen.blit(label2, (110 + label1.get_width(), 140))
    screen.blit(label3, (110, 170))
    screen.blit(label4, (110 + label3.get_width(), 170))
    # Blinking cursor
    if cursor_visible:
        if input_field == 0:
            cursor_at = 110 + label1.get_width() + label2.get_width()
            pygame.draw.line(screen, (0, 255, 0), (cursor_at, 140), (cursor_at, 158), 2)
        else:
            cursor_at = 110 + label3.get_width() + label4.get_width()
            pygame.draw.line(screen, (0, 255, 0), (cursor_at, 170), (cursor_at, 188), 2)

# Add the following utility functions above the main loop:
def pointer_is_on_map():
    mx, my = pygame.mouse.get_pos()
    if mx > VIEW_WIDTH * TILE_WIDTH or my > VIEW_HEIGHT * TILE_HEIGHT:
        return -1, -1
    x, y = mx // TILE_WIDTH + camera_x, my // TILE_HEIGHT + camera_y
    return x, y

def insert_row(above=True):
    x, y = pointer_is_on_map()
    if x < 0:
        return
    fill_char = char_list[0]
    new_row = [fill_char] * len(ascii_map[0])
    index = y if above else y + 1
    ascii_map.insert(index, new_row)
    for obj in objects_data.values():
        if obj['y'] >= index:
            obj['y'] += 1
    undo_stack.append(snapshot())
    redo_stack.clear()

def remove_row():
    x, y = pointer_is_on_map()
    if x < 0:
        return
    if 0 <= y < len(ascii_map):
        ascii_map.pop(y)
        to_delete = [k for k, v in objects_data.items() if v['y'] == y]
        for k in to_delete:
            del objects_data[k]
        for obj in objects_data.values():
            if obj['y'] > y:
                obj['y'] -= 1
        undo_stack.append(snapshot())
        redo_stack.clear()

def insert_column(before=True):
    x, y = pointer_is_on_map()
    if x < 0:
        return
    fill_char = char_list[0]
    for row in ascii_map:
        index = x if before else x + 1
        row.insert(index, fill_char)
    for obj in objects_data.values():
        if obj['x'] >= index:
            obj['x'] += 1
    undo_stack.append(snapshot())
    redo_stack.clear()

def remove_column():
    x, y = pointer_is_on_map()
    if x < 0:
        return
    if 0 <= x < len(ascii_map[0]):
        for row in ascii_map:
            row.pop(x)
        to_delete = [k for k, v in objects_data.items() if v['x'] == x]
        for k in to_delete:
            del objects_data[k]
        for obj in objects_data.values():
            if obj['x'] > x:
                obj['x'] -= 1
        undo_stack.append(snapshot())
        redo_stack.clear()
def snapshot():
    return {
        "ascii_map": copy.deepcopy(ascii_map),
        "objects_data": copy.deepcopy(objects_data)
    }

def apply_snapshot(state):
    global ascii_map, objects_data
    ascii_map = copy.deepcopy(state["ascii_map"])
    objects_data = copy.deepcopy(state["objects_data"])
running = True
while running:
    screen.fill((50, 50, 50))

    # Timer update for cursor
    cursor_timer += clock.get_time()
    if cursor_timer >= cursor_interval:
        cursor_visible = not cursor_visible
        cursor_timer = 0

    for y in range(VIEW_HEIGHT):
        for x in range(VIEW_WIDTH):
            map_x, map_y = camera_x + x, camera_y + y
            if 0 <= map_y < len(ascii_map) and 0 <= map_x < len(ascii_map[0]):
                char = ascii_map[map_y][map_x]
                tile = tdb.tiles[tile_map[char]]
                rect = pygame.Rect(x*TILE_WIDTH, y*TILE_HEIGHT, TILE_WIDTH, TILE_HEIGHT)
                if tile.image:
                    pass
                else:
                    color = tdb.tiles[tile_map[char]].color
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
                label = FONT.render(char, True, (0, 0, 0))
                screen.blit(label, (x*TILE_WIDTH + ascii_offset_x, y*TILE_HEIGHT + ascii_offset_y))

    for name, obj in objects_data.items():
        ox, oy = obj["x"], obj["y"]
        map_x, map_y = ox - camera_x, oy - camera_y
        if 0 <= map_x < VIEW_WIDTH and 0 <= map_y < VIEW_HEIGHT:
            obj_type = obj.get("object_type")
            col = odb.obj_templates[obj_type].color
            pygame.draw.circle(screen, col, (map_x*TILE_WIDTH + TILE_WIDTH//2, map_y*TILE_HEIGHT + TILE_HEIGHT//2), 6)

    draw_sidebar()
    if input_mode: draw_input_box()
    if arg_input_mode: draw_arg_input_box()
    if ghost_object:
        gx, gy = ghost_object["x"] - camera_x, ghost_object["y"] - camera_y
        if 0 <= gx < VIEW_WIDTH and 0 <= gy < VIEW_HEIGHT:
            screen_x = gx * TILE_WIDTH
            screen_y = gy * TILE_HEIGHT
            pygame.draw.circle(screen, (255, 255, 255), (screen_x + 16, screen_y + 16), 6, 2)
    # Tooltips for hovered objects
    tx, ty = pointer_is_on_map()
    if not tx < 0:
        for name, obj in objects_data.items():
            if obj["x"] == tx and obj["y"] == ty:
                screen_x = (obj["x"] - camera_x) * VIEW_WIDTH
                screen_y = (obj["y"] - camera_y) * VIEW_HEIGHT
                draw_tooltip(name, obj["object_type"], screen_x, screen_y)
                break

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()

            if input_mode:
                if event.key == pygame.K_RETURN and input0 and input1:
                    if input0 in char_list:
                        print("Please choose a unique tile representative.")
                        continue
                    if input1 not in tdb.tiles:
                        print(f"{input1} is not a valid tile.")
                        continue
                    tile_map[input0] = input1
                    char_list = list(tile_map.keys())
                    input_mode = False
                    input_field = 0
                    input1 = ""
                if event.key == pygame.K_ESCAPE:
                    input_mode = False
                    input_field = 0
                    input1 = ""
                elif event.key == pygame.K_BACKSPACE:
                    if input1:
                        input1 = input1[:-1]
                    elif input0:
                        input0 = input0[:-1]
                elif event.key == pygame.K_TAB:
                    input_field = 1 - input_field  # Toggle between 0 and 1
                else:
                    if input_field == 0 and len(input0) < 1:
                        input0 += event.unicode
                    elif input_field == 1 and len(input1) < 20:
                        input1 += event.unicode
            elif arg_input_mode:
                if event.key == pygame.K_RETURN:
                    input_field = 0
                    if input0 and input1:
                        split_input0 = input0.split("__")
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
                        recursive_dicts(arg_input_args, split_input0, input1)
                        input0 = ""
                        input1 = ""
                    else:
                        if pending_object:
                            if "name" not in arg_input_args:
                                print("Please include a name at minimum")
                                input0 = "name"
                                continue
                            name = arg_input_args.pop("name")
                            pending_object["args"] = arg_input_args
                            objects_data[name] = pending_object
                        arg_input_mode = False
                        arg_input_args = {}
                        input0 = ""
                        input1 = ""
                        pending_object = None
                elif event.key == pygame.K_ESCAPE:
                    arg_input_mode = False
                    arg_input_args = {}
                    input0 = ""
                    input1 = ""
                    pending_object = None
                elif event.key == pygame.K_BACKSPACE:
                    if input_field == 1 and input1:
                        input1 = input1[:-1]
                    elif input0:
                        input0 = input0[:-1]
                elif event.key == pygame.K_TAB:
                    input_field = 1 - input_field  # Toggle between 0 and 1
                else:
                    if input_field == 0 and len(input0) < 20:
                        input0 += event.unicode
                    elif input_field == 1 and len(input1) < 80:
                        input1 += event.unicode

            else:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_TAB:
                    placing_mode = "object" if placing_mode == "tile" else "tile"
                elif event.key == pygame.K_z:
                    if mods & pygame.KMOD_CTRL:
                        if undo_stack:
                            redo_stack.append(snapshot())
                            apply_snapshot(undo_stack.pop())
                    else:
                        input_mode = True
                        input0 = ""
                elif event.key == pygame.K_y:
                    if mods & pygame.KMOD_CTRL:
                        if redo_stack:
                            undo_stack.append(snapshot())
                            apply_snapshot(redo_stack.pop())
                elif event.key in [pygame.K_RIGHT, pygame.K_LEFT, pygame.K_UP, pygame.K_DOWN]:
                    if mods & pygame.KMOD_CTRL:
                        if event.key == pygame.K_RIGHT and ascii_offset_x < TILE_WIDTH:
                            ascii_offset_x += 1
                        if event.key == pygame.K_LEFT and ascii_offset_x > 0:
                            ascii_offset_x -= 1
                        if event.key == pygame.K_DOWN and ascii_offset_y < TILE_HEIGHT:
                            ascii_offset_y += 1
                        if event.key == pygame.K_UP and ascii_offset_y > 0:
                            ascii_offset_y -= 1
                    elif event.key in [pygame.K_RIGHT, pygame.K_LEFT]:
                        if placing_mode == "tile":
                            tile_index = (tile_index + (1 if event.key == pygame.K_RIGHT else -1)) % len(char_list)
                        else:
                            object_index = (object_index + (1 if event.key == pygame.K_RIGHT else -1)) % len(object_types)
                            selected_object_type = object_types[object_index]
                elif event.key == pygame.K_w:  # Insert row above cursor
                    if mods & pygame.KMOD_SHIFT: camera_y = max(camera_y - 1, 0)
                    else: insert_row(above=True)
                elif event.key == pygame.K_s:  # Insert row below cursor
                    if mods & pygame.KMOD_SHIFT: camera_y = min(camera_y + 1, len(ascii_map) - VIEW_HEIGHT)
                    else: insert_row(above=False)
                elif event.key == pygame.K_a:  # Insert column before cursor
                    if mods & pygame.KMOD_CTRL:
                        full_map_mode = not full_map_mode
                        if full_map_mode:
                            VIEW_WIDTH, VIEW_HEIGHT = min(27, len(ascii_map[0])), min(20, len(ascii_map))
                        else:
                            VIEW_WIDTH, VIEW_HEIGHT = 13, 13
                        camera_x, camera_y = 0, 0
                        SCREEN_WIDTH, SCREEN_HEIGHT = TILE_WIDTH * VIEW_WIDTH + SIDEBAR_SPACE_WIDTH, TILE_HEIGHT * VIEW_HEIGHT + SIDEBAR_SPACE_HEIGHT  # Extra space for sidebar
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                    elif mods & pygame.KMOD_SHIFT:
                        camera_x = max(camera_x - 1, 0)
                    else:
                        insert_column(before=True)
                elif event.key == pygame.K_d:  # Insert column after cursor
                    if mods & pygame.KMOD_SHIFT: camera_x = min(camera_x + 1, len(ascii_map[0]) - VIEW_WIDTH)
                    else: insert_column(before=False)
                elif event.key == pygame.K_r:  # Remove row at cursor
                    remove_row()
                elif event.key == pygame.K_c:  # Remove column at cursor
                    remove_column()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            tx, ty = pointer_is_on_map()
            if tx < 0:
                continue
            mods = pygame.key.get_mods()
            keys_at_tile = [k for k,v in objects_data.items() if v["x"] == tx and v["y"] == ty]
            if event.button == 1 and not (input_mode or arg_input_mode):

                if placing_mode == "tile":
                    if mods & pygame.KMOD_SHIFT:
                        paint_tiles.append((tx, ty))
                        if len(paint_tiles) < 2:
                            continue
                        tx0, ty0 = paint_tiles[0]
                        tx1, ty1 = paint_tiles[1]
                        tx_range = range(tx0, tx1 + 1) if tx0 <= tx1 else range(tx1, tx0 + 1)
                        ty_range = range(ty0, ty1 + 1) if ty0 <= ty1 else range(ty1, ty0 + 1)
                        for i in tx_range:
                            for j in ty_range:
                                if not tdb.tiles[tile_map[char_list[tile_index]]].is_passable:
                                    keys_at_tile = [k for k,v in objects_data.items() if v["x"] == i and v["y"] == j]
                                    if keys_at_tile:
                                        continue
                                ascii_map[j][i] = char_list[tile_index]
                        paint_tiles = []
                    if mods & pygame.KMOD_CTRL:
                        tile_index = next((i for i, val in enumerate(char_list) if val == ascii_map[ty][tx]), None)
                    if keys_at_tile and not tdb.tiles[tile_map[char_list[tile_index]]].is_passable:
                        continue
                    ascii_map[ty][tx] = char_list[tile_index]
                    mouse_dragging = True
                    last_dragged_tiles.clear()
                    last_dragged_tiles.add((tx, ty))
                else:
                    if mods & pygame.KMOD_SHIFT:
                        dragged_object_key = keys_at_tile[0]
                        ghost_object = obj.copy()
                        continue
                    not_already_occupied = True
                    if not tdb.tiles[tile_map[ascii_map[ty][tx]]].is_passable:
                        continue
                    if not odb.obj_templates[selected_object_type].is_passable:
                        not_already_occupied = all(odb.obj_templates[objects_data[k]["object_type"]].is_passable() for k in keys_at_tile)
                            
                    if not_already_occupied:
                        pending_object = {
                            "object_type": selected_object_type,
                            "x": tx,
                            "y": ty,
                            "args": {}
                        }
                        arg_input_mode = True
                        input0 = "name"
                        input_field = 1
                    
                undo_stack.append(snapshot())
                redo_stack.clear()
            elif event.button == 3:
                for k in keys_at_tile:
                    del objects_data[k]
        elif event.type == pygame.MOUSEMOTION:
            tx, ty = pointer_is_on_map()
            keys_at_tile = [k for k,v in objects_data.items() if v["x"] == tx and v["y"] == ty]
            if mouse_dragging and placing_mode == "tile":
                if (tx, ty) not in last_dragged_tiles:
                    if keys_at_tile and not tdb.tiles[tile_map[char_list[tile_index]]].is_passable:
                        continue
                    ascii_map[ty][tx] = char_list[tile_index]
                    last_dragged_tiles.add((tx, ty))
            elif dragged_object_key and ghost_object:
                if keys_at_tile or not tdb.tiles[tile_map[ascii_map[ty][tx]]].is_passable:
                    continue
                ghost_object["x"] = tx
                ghost_object["y"] = ty

        # Inside event loop, MOUSEBUTTONUP:
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if dragged_object_key and ghost_object:
                    objects_data[dragged_object_key]["x"] = ghost_object["x"]
                    objects_data[dragged_object_key]["y"] = ghost_object["y"]
                dragged_object_key = None
                ghost_object = None
                mouse_dragging = False
                last_dragged_tiles.clear()

    pygame.display.flip()
    clock.tick(30)

with open(ascii_path, "w") as f:
    for row in ascii_map:
        f.write("".join(row) + "\n")
with open(objects_path, "w") as f:
    sorted_dict = {key: objects_data[key] for key in sorted(objects_data)}
    for key in sorted_dict:
        args = sorted_dict[key].pop("args", None)
        if args:
            sorted_dict[key]["args"] = args
    json.dump(sorted_dict, f, indent=2)
with open(tiles_path, "w") as f:
    json.dump(tile_map, f, indent=2)

pygame.quit()