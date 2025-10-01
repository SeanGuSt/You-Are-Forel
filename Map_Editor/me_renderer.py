import pygame
from typing import TYPE_CHECKING
from Map_Editor.me_constants import *
if TYPE_CHECKING:
    from Map_Editor.map_editor import MapEditor

class Renderer:
    def __init__(self, engine: 'MapEditor', FONT):
        self.engine = engine
        self.FONT = FONT
    def draw_tooltips(self, tx, ty, camera_x, camera_y, objects_data):
        offset = 0
        for name, obj in objects_data.items():
            if obj["position"] == [tx, ty]:
                obj_type = obj.get("object_type", "unknown")
                screen_x = obj["position"][0] * TILE_WIDTH
                screen_y = obj["position"][1] * TILE_HEIGHT + offset
                offset += self.draw_tooltip(name, obj_type, screen_x, screen_y)
        return offset
    def draw_tooltip(self, name, obj_type, screen_x, screen_y):
        screen = self.engine.screen
        text = f"{name} ({obj_type})"
        surf = self.FONT.render(text, True, (255, 255, 255))
        bg = pygame.Surface((surf.get_width() + 6, surf.get_height() + 4))
        bg.fill((0, 0, 0))
        screen.blit(bg, (screen_x + 10, screen_y - 10))
        screen.blit(surf, (screen_x + 13, screen_y - 8))
        return surf.get_height() + 4
    def draw_sidebar(self):
        # UI Helpers
        screen = self.engine.screen
        sidebar_rect = pygame.Rect(SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH, 0, SIDEBAR_SPACE_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(screen, (30, 30, 30), sidebar_rect)
        pygame.draw.line(screen, (100, 100, 100), (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH, 0), (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH, SCREEN_HEIGHT))
        title = self.FONT.render("Map Editor", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 10))
        mode = self.FONT.render(f"Mode: {self.engine.placing_mode}", True, (255, 255, 0))
        screen.blit(mode, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 40))
        if self.engine.placing_mode == "tile":
            tile_ascii = self.engine.char_list[self.engine.tile_index]
            tile_text = self.FONT.render(f"Tile: '{tile_ascii}': {self.engine.tile_map[tile_ascii]}", True, (255, 255, 255))
            screen.blit(tile_text, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 70))
        else:
            obj = self.engine.object_types[self.engine.object_index]
            obj_text = self.FONT.render(f"Node: {obj}", True, (255, 255, 255))
            screen.blit(obj_text, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 20, 70))
        controls = [
            "[TAB] Toggle Mode",
            "[<-]/[->] Cycle Tile/Node",
            "[z] Add Tile",
            "[wasd] Insert Row/Column at Cursor",
            "[r] Remove Row at Cursor",
            "[c] Remove Column at Cursor",
            "[Shift+wasd] Scroll Map",
            "[Click] Place",
            "[Shift+Click] Paint Area with Tile",
            "[Ctrl+Click] Cycle to Tile/Node",
            "[Right Click] Delete Nodes at Tile",
            "[Ctrl+z] Undo",
            "[Ctrl+y] Redo",
            "[Alt+Click] Elevation +1 of tile at Cursor",
            "[Ctrl+Alt+Click] All Like Tile Elevations +1",
            "[Alt+Right Click] Elevation -1 of tile at Cursor",
            "[Ctrl+Alt+Right Click] All Like Tile Elevations -1",
            "[ESC] Exit"
        ]
        for i, line in enumerate(controls):
            label = self.FONT.render(line, True, (200, 200, 200))
            screen.blit(label, (SCREEN_WIDTH - SIDEBAR_SPACE_WIDTH + 10, 120 + i * 25))

    def draw_input_box(self, input0: str, input1: str, label_1: str = "", label_3: str = ""):
        screen = self.engine.screen
        pygame.draw.rect(screen, (0, 0, 0), (100, 100, 420, 180))
        pygame.draw.rect(screen, (255, 255, 255), (100, 100, 420, 180), 2)
        label_0 = "Enter object args (key:value)"
        label0 = self.FONT.render(label_0, True, (255, 255, 255))
        label1 = self.FONT.render(label_1, True, (255, 255, 255))
        label2 = self.FONT.render(input0, True, (0, 255, 0))
        label3 = self.FONT.render(label_3, True, (255, 255, 255))
        label4 = self.FONT.render(input1, True, (0, 255, 0))
        screen.blit(label0, (110, 110))
        screen.blit(label1, (110, 140))
        screen.blit(label2, (110 + label1.get_width(), 140))
        screen.blit(label3, (110, 170))
        screen.blit(label4, (110 + label3.get_width(), 170))
        # Blinking cursor
        if self.engine.cursor_visible:
            if self.engine.input_field == 0:
                cursor_at = 110 + label1.get_width() + label2.get_width()
                pygame.draw.line(screen, (0, 255, 0), (cursor_at, 140), (cursor_at, 158), 2)
            else:
                cursor_at = 110 + label3.get_width() + label4.get_width()
                pygame.draw.line(screen, (0, 255, 0), (cursor_at, 170), (cursor_at, 188), 2)

    def draw_ghost_object(self, ghost_object, camera_x, camera_y):
        gx, gy = ghost_object["position"][0] - camera_x, ghost_object["position"][1] - camera_y
        pygame.draw.circle(self.engine.screen, (0, 255, 0), (gx * TILE_WIDTH + TILE_WIDTH // 2, gy * TILE_HEIGHT + TILE_HEIGHT // 2), 6)

    def render_map(self):
        screen = self.engine.screen
        tdb = self.engine.tdb
        ascii_map = self.engine.ascii_map
        level_map = self.engine.levels_map
        tile_map = self.engine.tile_map
        for y in range(VIEW_HEIGHT):
            for x in range(VIEW_WIDTH):
                map_x, map_y = self.engine.camera_x + x, self.engine.camera_y + y
                if 0 <= map_y < len(ascii_map) and 0 <= map_x < len(ascii_map[0]):
                    char = ascii_map[map_y][map_x]
                    level = level_map[map_y][map_x]
                    tile = tdb.tiles[tile_map[char]]
                    rect = pygame.Rect(x*TILE_WIDTH, y*TILE_HEIGHT, TILE_WIDTH, TILE_HEIGHT)
                    if tile.image:
                        pass
                    else:
                        color = tdb.tiles[tile_map[char]].color
                    pygame.draw.rect(screen, color, rect)
                    pygame.draw.rect(screen, (0, 0, 0), rect, 1)
                    label = self.FONT.render(char + str(level), True, (0, 0, 0))
                    screen.blit(label, (x*TILE_WIDTH + ascii_offset_x, y*TILE_HEIGHT + ascii_offset_y))
    
    def render_objects(self):
        ghost_object = self.engine.ghost_object
        screen = self.engine.screen
        camera_x = self.engine.camera_x
        camera_y = self.engine.camera_y
        for name, obj in self.engine.objects_data.items():
            ox, oy = obj["position"]
            map_x, map_y = ox - camera_x, oy - camera_y
            if 0 <= map_x < VIEW_WIDTH and 0 <= map_y < VIEW_HEIGHT:
                obj_type = obj.get("object_type")
                col = self.engine.odb.obj_templates[obj_type].color
                pygame.draw.circle(screen, col, (map_x*TILE_WIDTH + TILE_WIDTH//2, map_y*TILE_HEIGHT + TILE_HEIGHT//2), 6)
        if ghost_object:
            gx, gy = ghost_object["position"][0] - camera_x, ghost_object["position"][1] - camera_y
            if 0 <= gx < VIEW_WIDTH and 0 <= gy < VIEW_HEIGHT:
                screen_x = gx * TILE_WIDTH
                screen_y = gy * TILE_HEIGHT
                pygame.draw.circle(screen, (255, 255, 255), (screen_x + 16, screen_y + 16), 6, 2)