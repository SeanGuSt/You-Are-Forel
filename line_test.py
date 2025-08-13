import pygame
import math
import random
from typing import Set, Tuple, List

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 20
MAP_WIDTH = SCREEN_WIDTH // TILE_SIZE
MAP_HEIGHT = SCREEN_HEIGHT // TILE_SIZE

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)

class GameMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.generation = 0
        # Create a simple map with some walls
        self.walls = set()
        self._create_random_walls()
    
    def _create_random_walls(self):
        """Create some random walls for testing"""
        # Add border walls
        for x in range(self.width):
            self.walls.add((x, 0))
            self.walls.add((x, self.height - 1))
        for y in range(self.height):
            self.walls.add((0, y))
            self.walls.add((self.width - 1, y))
        
        # Add some random interior walls
        for _ in range(50):
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)
            self.walls.add((x, y))
    
    def can_see_thru(self, pos: Tuple[int, int]) -> bool:
        """Return True if we can see through this position"""
        return pos not in self.walls
    
    def is_wall(self, pos: Tuple[int, int]) -> bool:
        """Return True if this position is a wall"""
        return pos in self.walls

class FOVRenderer:
    def __init__(self, game_map: GameMap):
        self.game_map = game_map
        self._fov_cache = {}
        self._fov_cache_key = None
        self.ray_colors = {}  # Store colors for each ray
        self.rays = []  # Store all rays for visualization
    
    def _bresenham_line(self, x0, y0, x1, y1):
        """Yield (x,y) points on a grid from (x0,y0) to (x1,y1) inclusive (integer coords)."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        x, y = x0, y0
        if dx >= dy:
            err = dx // 2
            while True:
                yield x, y
                if x == x1 and y == y1:
                    break
                x += sx
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
        else:
            err = dy // 2
            while True:
                yield x, y
                if x == x1 and y == y1:
                    break
                y += sy
                err -= dx
                if err < 0:
                    x += sx
                    err += dy

    def get_visible_positions_with_rays(self, observer_pos, max_distance=8):
        """
        Modified version that stores rays for visualization
        """
        ox, oy = observer_pos
        visible = set()
        visible.add((ox, oy))
        
        self.rays.clear()  # Clear previous rays
        self.ray_colors.clear()

        radius = int(max_distance)
        
        # Get perimeter points
        perim_points = []
        for dx in range(-radius, radius + 1):
            perim_points.append((ox + dx, oy - radius))  # top row
            perim_points.append((ox + dx, oy + radius))  # bottom row
        for dy in range(-radius + 1, radius):  # avoid double-adding corners
            perim_points.append((ox - radius, oy + dy))  # left column
            perim_points.append((ox + radius, oy + dy))  # right column

        seen = set()
        perim = []
        for p in perim_points:
            if p not in seen:
                seen.add(p)
                perim.append(p)

        # Cast ray to each perimeter point
        map_w = self.game_map.width
        map_h = self.game_map.height

        ray_index = 0
        for tx, ty in perim:
            # Generate a unique color for this ray
            hue = (ray_index * 137.5) % 360  # Golden angle for good color distribution
            color = self._hsv_to_rgb(hue, 0.8, 0.9)
            
            ray_points = []
            for x, y in self._bresenham_line(ox, oy, tx, ty):
                if ox == x and oy == y:
                    continue
                if x < 0 or y < 0 or x >= map_w or y >= map_h:
                    break

                ray_points.append((x, y))
                visible.add((x, y))

                if not self.game_map.can_see_thru((x, y)):
                    # include the blocking tile but stop the ray
                    break
            
            if ray_points:  # Only store rays that have points
                self.rays.append(ray_points)
                self.ray_colors[ray_index] = color
                ray_index += 1

        return visible
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB"""
        h = h / 60.0
        c = v * s
        x = c * (1 - abs(h % 2 - 1))
        m = v - c
        
        if 0 <= h < 1:
            r, g, b = c, x, 0
        elif 1 <= h < 2:
            r, g, b = x, c, 0
        elif 2 <= h < 3:
            r, g, b = 0, c, x
        elif 3 <= h < 4:
            r, g, b = 0, x, c
        elif 4 <= h < 5:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))

class RayVisualizerGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Bresenham Ray FOV Visualizer")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Create game objects
        self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
        self.fov_renderer = FOVRenderer(self.game_map)
        
        # Player position
        self.player_pos = (MAP_WIDTH // 2, MAP_HEIGHT // 2)
        self.fov_radius = 8
        
        # Visualization settings
        self.show_rays = True
        self.show_visible = True
        self.show_grid = True
        
        # Font for instructions
        self.font = pygame.font.Font(None, 24)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.show_rays = not self.show_rays
                elif event.key == pygame.K_v:
                    self.show_visible = not self.show_visible
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key == pygame.K_SPACE:
                    # Regenerate map
                    self.game_map = GameMap(MAP_WIDTH, MAP_HEIGHT)
                    self.fov_renderer = FOVRenderer(self.game_map)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Move player to mouse position
                mouse_x, mouse_y = pygame.mouse.get_pos()
                tile_x = mouse_x // TILE_SIZE
                tile_y = mouse_y // TILE_SIZE
                if (0 <= tile_x < MAP_WIDTH and 0 <= tile_y < MAP_HEIGHT and 
                    not self.game_map.is_wall((tile_x, tile_y))):
                    self.player_pos = (tile_x, tile_y)
    
    def render(self):
        self.screen.fill(BLACK)
        
        # Get visible positions and rays
        visible_positions = self.fov_renderer.get_visible_positions_with_rays(
            self.player_pos, self.fov_radius
        )
        
        # Draw grid
        if self.show_grid:
            for x in range(0, SCREEN_WIDTH, TILE_SIZE):
                pygame.draw.line(self.screen, DARK_GRAY, (x, 0), (x, SCREEN_HEIGHT))
            for y in range(0, SCREEN_HEIGHT, TILE_SIZE):
                pygame.draw.line(self.screen, DARK_GRAY, (0, y), (SCREEN_WIDTH, y))
        
        # Draw map tiles
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                
                if self.game_map.is_wall((x, y)):
                    pygame.draw.rect(self.screen, GRAY, rect)
                elif self.show_visible and (x, y) in visible_positions:
                    pygame.draw.rect(self.screen, (32, 32, 32), rect)
        
        # Draw rays
        if self.show_rays:
            ox, oy = self.player_pos
            for i, ray_points in enumerate(self.fov_renderer.rays):
                if i in self.fov_renderer.ray_colors:
                    color = self.fov_renderer.ray_colors[i]
                    
                    # Draw ray as connected line segments
                    points = [(ox * TILE_SIZE + TILE_SIZE // 2, oy * TILE_SIZE + TILE_SIZE // 2)]
                    for x, y in ray_points:
                        points.append((x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2))
                    
                    if len(points) > 1:
                        pygame.draw.lines(self.screen, color, False, points, 2)
        
        # Draw player
        px, py = self.player_pos
        player_rect = pygame.Rect(px * TILE_SIZE + 2, py * TILE_SIZE + 2, 
                                 TILE_SIZE - 4, TILE_SIZE - 4)
        pygame.draw.rect(self.screen, RED, player_rect)
        
        # Draw FOV radius circle outline
        center = (px * TILE_SIZE + TILE_SIZE // 2, py * TILE_SIZE + TILE_SIZE // 2)
        pygame.draw.circle(self.screen, WHITE, center, self.fov_radius * TILE_SIZE, 1)
        
        # Draw instructions
        instructions = [
            "Click to move player",
            "R - Toggle rays",
            "V - Toggle visible tiles", 
            "G - Toggle grid",
            "SPACE - New map",
            "ESC - Quit"
        ]
        
        y_offset = 10
        for instruction in instructions:
            text = self.font.render(instruction, True, WHITE)
            self.screen.blit(text, (10, y_offset))
            y_offset += 25
        
        # Draw stats
        stats = [
            f"Rays cast: {len(self.fov_renderer.rays)}",
            f"Visible tiles: {len(visible_positions)}",
            f"FOV radius: {self.fov_radius}"
        ]
        
        y_offset = SCREEN_HEIGHT - 75
        for stat in stats:
            text = self.font.render(stat, True, WHITE)
            self.screen.blit(text, (10, y_offset))
            y_offset += 25
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            self.handle_events()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    game = RayVisualizerGame()
    game.run()