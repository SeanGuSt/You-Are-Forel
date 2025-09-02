import pygame
import sys
import math
import time

# Initialize Pygame
pygame.init()

# Constants
TILE_WIDTH = 60
TILE_HEIGHT = 60
GRID_SIZE = 9
WINDOW_WIDTH = GRID_SIZE * TILE_WIDTH
WINDOW_HEIGHT = GRID_SIZE * TILE_HEIGHT + 100  # Extra space for UI

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

class Entity:
    def __init__(self, x, y, width, height, visible=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.visible = visible
        self.rect = pygame.Rect(x * TILE_WIDTH, y * TILE_HEIGHT, width, height)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("9x9 Grid Entity Group Game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        
        # Game state
        self.obj_width = 0
        self.obj_height = 0
        self.true_width = 0
        self.true_height = 0
        self.obj_group = []
        self.input_mode = False
        self.input_text = ""
        self.input_stage = 0  # 0 = width, 1 = height
        
        # Rotation state
        self.is_rotating = False
        self.rotation_start_time = 0
        self.rotation_duration = 20.0
        self.original_pattern = []  # Store original visible pattern
        
    def handle_input(self, event):
        if self.input_mode:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        value = int(self.input_text)
                        if self.input_stage == 0:  # Getting width
                            self.obj_width = value
                            self.input_stage = 1
                            self.input_text = ""
                        else:  # Getting height
                            self.obj_height = value
                            self.create_entity_group()
                            self.input_mode = False
                            self.input_stage = 0
                            self.input_text = ""
                    except ValueError:
                        self.input_text = ""
                elif event.key == pygame.K_ESCAPE:
                    self.input_mode = False
                    self.input_stage = 0
                    self.input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                elif event.unicode.isdigit():
                    self.input_text += event.unicode
        else:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d:
                    self.input_mode = True
                    self.input_stage = 0
                    self.input_text = ""
                elif event.key == pygame.K_r and self.obj_group and not self.is_rotating:
                    self.start_rotation()
    
    def create_entity_group(self):
        # Calculate true dimensions
        if self.obj_height == self.obj_width:
            self.true_width = self.obj_width
            self.true_height = self.obj_height
        else:
            self.true_width = 2 * max(self.obj_width, self.obj_height) - 1
            self.true_height = 2 * max(self.obj_width, self.obj_height) - 1
        
        # Clear previous group
        self.obj_group = []
        
        # Create the full grid of entities (true_width x true_height)
        center_x = self.true_width // 2
        center_y = self.true_height // 2
        
        for y in range(self.true_height):
            row = []
            for x in range(self.true_width):
                # All entities start as invisible
                entity = Entity(x, y, TILE_WIDTH, TILE_HEIGHT, visible=False)
                row.append(entity)
            self.obj_group.append(row)
        
        # Make entities visible according to the rules:
        # 1. Center tile is always rendered
        # 2. Upper-left tiles are used to fill obj_width x obj_height
        
        # First, make center tile visible
        if self.obj_group:
            self.obj_group[center_y][center_x].visible = True
        
        # Calculate the starting position for the obj_width x obj_height rectangle
        # We want it to include the center and favor upper-left positioning
        start_x = center_x - (self.obj_width - 1) // 2
        start_y = center_y - (self.obj_height - 1) // 2
        
        # Adjust if we go out of bounds (favor upper-left)
        if start_x < 0:
            start_x = 0
        if start_y < 0:
            start_y = 0
        if start_x + self.obj_width > self.true_width:
            start_x = self.true_width - self.obj_width
        if start_y + self.obj_height > self.true_height:
            start_y = self.true_height - self.obj_height
        
        # Make the obj_width x obj_height rectangle visible
        for y in range(start_y, start_y + self.obj_height):
            for x in range(start_x, start_x + self.obj_width):
                if 0 <= y < self.true_height and 0 <= x < self.true_width:
                    self.obj_group[y][x].visible = True
        
        # Store the original pattern for rotation
        self.store_original_pattern()
    
    def store_original_pattern(self):
        """Store the original visible pattern relative to center for rotation"""
        if not self.obj_group:
            return
            
        self.original_pattern = []
        center_x = self.true_width // 2
        center_y = self.true_height // 2
        
        for y in range(self.true_height):
            for x in range(self.true_width):
                if self.obj_group[y][x].visible:
                    # Store relative position from center
                    rel_x = x - center_x
                    rel_y = y - center_y
                    self.original_pattern.append((rel_x, rel_y))
    
    def start_rotation(self):
        """Start the rotation animation"""
        if self.obj_height == self.obj_width:
            return
        self.is_rotating = True
        self.rotation_start_time = time.time()
    
    def update_rotation(self):
        """Update the rotation animation"""
        if not self.is_rotating:
            return
            
        current_time = time.time()
        elapsed = current_time - self.rotation_start_time
        
        if elapsed >= self.rotation_duration:
            # Rotation complete, restore original pattern
            self.is_rotating = False
            self.restore_original_pattern()
            return
        
        # Calculate rotation angle (0 to 2pi over 5 seconds)
        angle = (elapsed / self.rotation_duration) * 2 * math.pi
        
        # Clear all visibility
        for y in range(self.true_height):
            for x in range(self.true_width):
                self.obj_group[y][x].visible = False
        
        # Apply rotation to original pattern
        center_x = self.true_width // 2
        center_y = self.true_height // 2
        
        visible_positions = set()
        
        for rel_x, rel_y in self.original_pattern:
            # Rotate the point
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            rotated_x = rel_x * cos_a - rel_y * sin_a
            rotated_y = rel_x * sin_a + rel_y * cos_a
            
            # Convert back to grid coordinates
            grid_x = round(rotated_x + center_x)
            grid_y = round(rotated_y + center_y)
            
            # Add to visible positions if within bounds
            if 0 <= grid_x < self.true_width and 0 <= grid_y < self.true_height:
                visible_positions.add((grid_x, grid_y))
        
        # Also add interpolated positions to create smoother rotation illusion
        # This creates the effect where more tiles become visible during rotation
        for rel_x, rel_y in self.original_pattern:
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            rotated_x = rel_x * cos_a - rel_y * sin_a
            rotated_y = rel_x * sin_a + rel_y * cos_a
            
            # Add nearby integer positions to simulate the rotating shape
            for dx in [-0.5, 0, 0.5]:
                for dy in [-0.5, 0, 0.5]:
                    grid_x = round(rotated_x + center_x + dx)
                    grid_y = round(rotated_y + center_y + dy)
                    
                    if (0 <= grid_x < self.true_width and 
                        0 <= grid_y < self.true_height):
                        # Only add if close enough to the rotated position
                        dist = math.sqrt((rotated_x + center_x - grid_x)**2 + 
                                       (rotated_y + center_y - grid_y)**2)
                        if dist <= 0.7:  # Threshold for visibility
                            visible_positions.add((grid_x, grid_y))
        
        # Set visibility for all calculated positions
        for grid_x, grid_y in visible_positions:
            self.obj_group[grid_y][grid_x].visible = True
    
    def restore_original_pattern(self):
        """Restore the original pattern after rotation"""
        # Clear all visibility
        for y in range(self.true_height):
            for x in range(self.true_width):
                self.obj_group[y][x].visible = False
        
        # Restore original pattern
        center_x = self.true_width // 2
        center_y = self.true_height // 2
        
        for rel_x, rel_y in self.original_pattern:
            grid_x = rel_x + center_x
            grid_y = rel_y + center_y
            if 0 <= grid_x < self.true_width and 0 <= grid_y < self.true_height:
                self.obj_group[grid_y][grid_x].visible = True
        
        # Store the original pattern for rotation
        self.store_original_pattern()
    
    def draw_grid(self):
        # Draw grid lines
        for x in range(GRID_SIZE + 1):
            pygame.draw.line(self.screen, GRAY, 
                           (x * TILE_WIDTH, 0), 
                           (x * TILE_WIDTH, GRID_SIZE * TILE_HEIGHT))
        
        for y in range(GRID_SIZE + 1):
            pygame.draw.line(self.screen, GRAY, 
                           (0, y * TILE_HEIGHT), 
                           (GRID_SIZE * TILE_WIDTH, y * TILE_HEIGHT))
    
    def draw_entities(self):
        if not self.obj_group:
            return
            
        # Calculate offset to center the group in the 9x9 grid
        grid_center_x = GRID_SIZE // 2
        grid_center_y = GRID_SIZE // 2
        group_center_x = self.true_width // 2
        group_center_y = self.true_height // 2
        
        offset_x = grid_center_x - group_center_x
        offset_y = grid_center_y - group_center_y
        
        for y in range(self.true_height):
            for x in range(self.true_width):
                screen_x = (x + offset_x) * TILE_WIDTH
                screen_y = (y + offset_y) * TILE_HEIGHT
                entity = self.obj_group[y][x]
                if entity.visible:
                    
                    # Only draw if within the 9x9 grid bounds
                    if (0 <= x + offset_x < GRID_SIZE and 
                        0 <= y + offset_y < GRID_SIZE):
                        pygame.draw.rect(self.screen, BLUE, 
                                       (screen_x, screen_y, TILE_WIDTH, TILE_HEIGHT))
                        pygame.draw.rect(self.screen, BLACK, 
                                       (screen_x, screen_y, TILE_WIDTH, TILE_HEIGHT), 2)
                else:
                    pygame.draw.rect(self.screen, BLACK, 
                                       (screen_x, screen_y, TILE_WIDTH, TILE_HEIGHT), 2)
    
    def draw_ui(self):
        y_offset = GRID_SIZE * TILE_HEIGHT + 10
        
        if self.input_mode:
            if self.input_stage == 0:
                prompt = f"Enter obj_width: {self.input_text}"
            else:
                prompt = f"Enter obj_height (obj_width={self.obj_width}): {self.input_text}"
            text = self.font.render(prompt, True, BLACK)
        else:
            info_lines = [
                "Press 'd' to enter dimensions, 'r' to rotate",
                f"obj_width: {self.obj_width}, obj_height: {self.obj_height}",
                f"true_width: {self.true_width}, true_height: {self.true_height}"
            ]
            if self.is_rotating:
                elapsed = time.time() - self.rotation_start_time
                remaining = max(0, self.rotation_duration - elapsed)
                info_lines.append(f"Rotating... {remaining:.1f}s remaining")
            
            for i, line in enumerate(info_lines):
                text = self.font.render(line, True, BLACK)
                self.screen.blit(text, (10, y_offset + i * 25))
            return
            
        self.screen.blit(text, (10, y_offset))
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_input(event)
            
            # Update rotation if active
            self.update_rotation()
            
            # Clear screen
            self.screen.fill(WHITE)
            
            # Draw everything
            self.draw_grid()
            self.draw_entities()
            self.draw_ui()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()