import pygame
from typing import List, TYPE_CHECKING
from constants import *
from quests.quests import QuestStep
from objects.characters import Party, Character
from objects.map_objects import Map, Node, NPC, Monster, ItemHolder, Teleporter, MapObject
from objects.object_templates import CombatStatsMixin
from objects.projectiles import BattleProjectile
from options import GameOptions
from combat import CombatManager

if TYPE_CHECKING:
    from ultimalike import GameEngine

font_name = "georgia"
class Renderer:
    def __init__(self, engine: 'GameEngine', screen):
        self.engine = engine
        self.screen = screen
        self.font = pygame.font.SysFont(font_name, 24)
        self.small_font = pygame.font.SysFont(font_name, 18)
        self.large_font = pygame.font.SysFont(font_name, 30)
        self.side_font = pygame.font.SysFont(font_name, 20)
        self.text_cache: dict[tuple[str, pygame.font.Font, tuple[int, int, int]], pygame.Surface] = {}
        self._fov_cache = None
        self._fov_cache_key = None
        self.fading = False
        self.alpha = 0
        self.alpha_change_rate = 0
        self.veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.veil.fill(BLACK)

    def smooth_movement(self, obj: Node):
        timer_manager = self.engine.event_manager.timer_manager
        if obj.group and obj.group.progress:
            progress = obj.group.progress
        else:
            # Get the exact same timer and progress that the camera uses
            actual_timer_name = self.engine.get_movement_timer_name(obj)
            
            if not timer_manager.is_active(actual_timer_name):
                # No animation - use exact position
                map_pos = obj.subtract_tuples(obj.position, self.engine.camera)
                screen_x = int(round(map_pos[0] * TILE_WIDTH))
                screen_y = int(round(map_pos[1] * TILE_HEIGHT))
                return screen_x, screen_y
            
            # Get progress and ensure it's bounded
            progress = timer_manager.get_progress(actual_timer_name)
            if obj.group:
                obj.group.progress = progress
        
        # Calculate interpolated world position
        dx, dy = obj.subtract_tuples(obj.position, obj.old_position)
        world_x = obj.old_position[0] + dx * progress
        world_y = obj.old_position[1] + dy * progress
        
        # Convert to screen coordinates with consistent rounding
        map_x = world_x - self.engine.camera[0]
        map_y = world_y - self.engine.camera[1]
        
        screen_x = int(round(map_x * TILE_WIDTH))
        screen_y = int(round(map_y * TILE_HEIGHT))
        if progress >= 1.0:
            obj.old_position = obj.position
        
        return screen_x, screen_y

    #@time_function("Render Map: ") 
    def render_map(self):
        game_map = self.engine.current_map
        camera = self.engine.camera
        show_grid = self.engine.options.show_grid
        cam_x, cam_y = camera

        tile_offset_x = cam_x % 1  # fractional offset in tile
        tile_offset_y = cam_y % 1

        pixel_offset_x = int(tile_offset_x * TILE_WIDTH)
        pixel_offset_y = int(tile_offset_y * TILE_HEIGHT)

        base_tile_x = int(cam_x)
        base_tile_y = int(cam_y)
        y0, y1 = 0, MAP_HEIGHT + 1
        x0, x1 = 0, MAP_WIDTH + 1#The tiles of the map to actually render
        observer_pos = self.engine.party.get_leader().position
        
        # Get visible positions
        visible_positions = self.get_visible_positions(observer_pos, MAP_WIDTH)
        
        # When rendering tiles, check visibility:
        for y in range(y0, y1):
            for x in range(x0, x1):
                map_x = base_tile_x + x  
                map_y = base_tile_y + y
                
                # Only render if visible
                if (map_x, map_y) in visible_positions:
                    # Your existing tile rendering code
                    tile = game_map.get_tile_lower((map_x, map_y))
                    screen_x = x * TILE_WIDTH - pixel_offset_x
                    screen_y = y * TILE_HEIGHT - pixel_offset_y
                    if tile:
                        if tile.image:
                            self.screen.blit(tile.image, (screen_x, screen_y))
                        else:
                            rect = pygame.Rect(screen_x, screen_y, TILE_WIDTH, TILE_HEIGHT)
                            pygame.draw.rect(self.screen, tile.color, rect)

                        if show_grid:
                            pygame.draw.rect(self.screen, BLACK, rect, 1)

        def bump_movement(screen_x, screen_y, obj):
            """Handle bump animation using TimerManager progress"""
            timer_manager = self.engine.event_manager.timer_manager
            
            if not timer_manager.is_active("player_bump"):
                return screen_x, screen_y
                
            # Get bump direction from the character
            dx, dy = obj.bump_direction.value
            
            # Get progress (0.0 to 1.0)
            progress = timer_manager.get_progress("player_bump")
            
            # Create a "bounce" effect - go out then come back
            if progress <= 0.5:
                # First half: move toward the obstacle
                half_progress = progress / 0.5  # Scale to 0-1 for first half
                offset_x = dx * (TILE_WIDTH // 5) * half_progress
                offset_y = dy * (TILE_HEIGHT // 5) * half_progress
            else:
                # Second half: move back to original position  
                half_progress = (progress - 0.5) / 0.5  # Scale to 0-1 for second half
                offset_x = dx * (TILE_WIDTH // 5) * (1 - half_progress)
                offset_y = dy * (TILE_HEIGHT // 5) * (1 - half_progress)
            
            screen_x += offset_x
            screen_y += offset_y
            
            # Clean up when animation completes
            if progress >= 1.0:
                obj.is_bumping = False
                obj.bump_direction = None
                
            return screen_x, screen_y
    
        # Render map objects
        timer_manager = self.engine.event_manager.timer_manager
        self.engine.update_camera()
        for i, layer in self.engine.current_map.objects_by_layer.items():
            for obj in layer:
                obj.update()
                if type(obj) == Node:  # No need to render nodes
                    continue
                if obj.position not in visible_positions: 
                    continue
                elif obj.__is__(Character):  # If this is a party member other than the leader, don't render them outside of combat.
                    if (not self.engine.state == GameState.COMBAT and not obj == self.engine.party.get_leader()):
                        continue
                    
                map_x, map_y = obj.subtract_tuples(obj.position, camera)
                
                if -1 <= map_x <= MAP_WIDTH and -1 <= map_y <= MAP_HEIGHT:
                    screen_x, screen_y = obj.multiply_tuples((map_x, map_y), (TILE_WIDTH, TILE_HEIGHT))
                    obj_in_walkers = obj in self.engine.event_manager.walkers
                    
                    if obj == self.engine.party.get_leader() and timer_manager.is_active("player_bump"):
                        screen_x, screen_y = bump_movement(screen_x, screen_y, obj)
                    else:
                        screen_x, screen_y = self.smooth_movement(obj)
                    
                    #Draw Health bar
                    if self.engine.state == GameState.COMBAT and obj.__is__(CombatStatsMixin):
                        pygame.draw.rect(self.screen, RED, (screen_x + TILE_WIDTH//4, screen_y - TILE_HEIGHT//8, TILE_WIDTH//2, TILE_HEIGHT//8))
                        percentage_health = obj.hp/obj.max_hp
                        pygame.draw.rect(self.screen, GREEN, (screen_x + TILE_WIDTH//4, screen_y - TILE_HEIGHT//8, percentage_health*TILE_WIDTH//2, TILE_HEIGHT//8))
                    if obj.image:
                        if obj != self.engine.party.get_leader() or not self.engine.event_manager.make_leader_invisible:
                            self.screen.blit(obj.image, (screen_x, screen_y))
                    elif obj.__is__(Character):
                        rect = pygame.Rect(screen_x + TILE_WIDTH//8, screen_y + TILE_HEIGHT//8, TILE_WIDTH*3//4, TILE_HEIGHT*3//4)
                        pygame.draw.ellipse(self.screen, obj.color, rect)
                    elif obj.__is__(ItemHolder):
                        pygame.draw.circle(self.screen, obj.color, 
                                        (screen_x + TILE_WIDTH//2, screen_y + TILE_HEIGHT//2), 4)
                    elif obj.__is__(NPC):
                        pygame.draw.rect(self.screen, obj.color, 
                                    (screen_x + + TILE_WIDTH//4, screen_y + TILE_HEIGHT//4, TILE_WIDTH//2, TILE_HEIGHT//2))
                    elif obj.__is__(Teleporter):
                        pygame.draw.circle(self.screen, obj.color, 
                                        (screen_x + TILE_WIDTH//2, screen_y + TILE_HEIGHT//2), 4)
                    elif obj.__is__(Monster):
                        pygame.draw.rect(self.screen, obj.color, 
                                        (screen_x + TILE_WIDTH//4, screen_y + TILE_HEIGHT//4, TILE_WIDTH//2, TILE_HEIGHT//2))
    
    def render_main_menu(self):
        self.screen.fill(BLACK)
        
        title = self.large_font.render(GAME_TITLE.upper(), self.engine.antialias_text, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 100))
        self.screen.blit(title, title_rect)
        
        menu_items = [
            "N - New Game",
            "L - Load Game", 
            "O - Options",
            "Q - Quit"
        ]
        
        for i, item in enumerate(menu_items):
            text = self.font.render(item, self.engine.antialias_text, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, 200 + i * 40))
            self.screen.blit(text, text_rect)
                    
    def render_stats_menu(self):
        party = self.engine.party
        self.screen.fill(BLACK)
        
        title = self.font.render("PARTY STATISTICS", self.engine.antialias_text, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//40, SCREEN_HEIGHT//30))
        
        y_offset = SCREEN_HEIGHT//10
        for i, member in enumerate(party.members):
            # Character name and level
            name_text = self.font.render(f"{member.name} (Level {member.level})", self.engine.antialias_text, WHITE)
            self.screen.blit(name_text, (SCREEN_WIDTH//40, y_offset))
            
            # Stats
            hp_text = self.small_font.render(f"HP: {member.hp}/{member.max_hp}", self.engine.antialias_text, WHITE)
            str_text = self.small_font.render(f"STR: {member.strength}", self.engine.antialias_text, WHITE)
            dex_text = self.small_font.render(f"DEX: {member.dexterity}", self.engine.antialias_text, WHITE)
            int_text = self.small_font.render(f"FAI: {member.faith}", self.engine.antialias_text, WHITE)
            exp_text = self.small_font.render(f"EXP: {member.experience}", self.engine.antialias_text, WHITE)
            pow_text = self.small_font.render(f"Power: {member.get_total_power()}", self.engine.antialias_text, WHITE)
            grd_text = self.small_font.render(f"Guard: {member.get_total_guard()}", self.engine.antialias_text, WHITE)

            
            self.screen.blit(hp_text, (SCREEN_WIDTH//20, y_offset + SCREEN_HEIGHT//24))
            self.screen.blit(str_text, (SCREEN_WIDTH//4, y_offset + SCREEN_HEIGHT//24))
            self.screen.blit(dex_text, (SCREEN_WIDTH//4, y_offset + SCREEN_HEIGHT//13))
            self.screen.blit(int_text, (3*SCREEN_WIDTH//8, y_offset + SCREEN_HEIGHT//24))
            self.screen.blit(exp_text, (3*SCREEN_WIDTH//8, y_offset + SCREEN_HEIGHT//13))
            self.screen.blit(pow_text, (SCREEN_WIDTH//2, y_offset + SCREEN_HEIGHT//24))
            self.screen.blit(grd_text, (SCREEN_WIDTH//2, y_offset + SCREEN_HEIGHT//13))
            
            y_offset += SCREEN_HEIGHT//8
            
        # Instructions
        instruction = self.small_font.render("Press ESC to return", True, YELLOW)
        self.screen.blit(instruction, (20, 19*SCREEN_HEIGHT//20))
        
    def render_inventory_menu(self):
        party = self.engine.party
        selected_item = self.engine.selected_equipment
        picking_item_to_show = self.engine.picking_item_to_show
        self.screen.fill(BLACK)
        
        title = self.font.render("INVENTORY", self.engine.antialias_text, WHITE)
        self.screen.blit(title, (20, 20))
        
        gold_text = self.font.render(f"Gold: {party.gold}", True, YELLOW)
        self.screen.blit(gold_text, (SCREEN_WIDTH//40, SCREEN_HEIGHT//12))
        
        y_offset = 90
        for i, item in enumerate(party.inventory):
            if i == selected_item:
                item_text = self.small_font.render(f"{item.name} x{item.quantity}", self.engine.antialias_text, YELLOW)
                self.screen.blit(item_text, (SCREEN_WIDTH//40, y_offset))
                lines = self._wrap_text(item.description, self.small_font, 2*SCREEN_WIDTH//3)
                for line in lines:
                    desc_text = self.small_font.render(f" {line}", self.engine.antialias_text, GRAY)
                    self.screen.blit(desc_text, (SCREEN_WIDTH//40, y_offset + 20))
                    y_offset += 25
            else:
                item_text = self.small_font.render(f"{item.name} x{item.quantity}", self.engine.antialias_text, WHITE)
                self.screen.blit(item_text, (SCREEN_WIDTH//40, y_offset))
            y_offset += SCREEN_HEIGHT//20
            
        # Instructions
        if picking_item_to_show:
            instruction = self.small_font.render("Press ESC to return", self.engine.antialias_text, YELLOW)
            self.screen.blit(instruction, (SCREEN_WIDTH//40, 19*SCREEN_HEIGHT//20))
    
    def render_equipment_menu(self):
        party = self.engine.party
        selected_member = self.engine.selected_member
        selected_slot = self.engine.selected_slot
        selected_equipment = self.engine.selected_equipment
        show_equipment_list = self.engine.show_equipment_list
        self.screen.fill(BLACK)
        
        title = self.font.render("EQUIPMENT", self.engine.antialias_text, WHITE)
        self.screen.blit(title, (20, 20))
        
        # Character selection
        char_text = self.font.render("Select Character:", self.engine.antialias_text, WHITE)
        self.screen.blit(char_text, (20, 60))
        
        for i, member in enumerate(party.members):
            color = YELLOW if i == selected_member else WHITE
            member_text = self.small_font.render(f"{i+1}. {member.name}", True, color)
            self.screen.blit(member_text, (40, 90 + i * 25))
        
        if party.members:
            current_member = party.members[selected_member]
            
            # Equipment slots
            slots_text = self.font.render(f"{current_member.name}'s Equipment:", self.engine.antialias_text, WHITE)
            self.screen.blit(slots_text, (300, 60))
            
            y_offset = 90
            for i, slot in enumerate(EquipmentSlot):
                color = YELLOW if i == selected_slot else WHITE
                equipped_item = current_member.equipped.get(slot.value)
                slot_name = slot.value.title()
                if equipped_item:
                    slot_text = f"{slot_name}: {equipped_item.name}"
                    if equipped_item.slot == EquipmentSlot.WEAPON:
                        slot_text += f" (Power: {equipped_item.power})"
                    elif equipped_item.slot == EquipmentSlot.ARMOR:
                        slot_text += f" (Guard: {equipped_item.guard})"
                else:
                    slot_text = f"{slot_name}: (None)"
                
                rendered = self.small_font.render(slot_text, True, color)
                self.screen.blit(rendered, (320, y_offset))
                if i == selected_slot and equipped_item:
                    lines = self._wrap_text(equipped_item.description, self.small_font, 2 * SCREEN_WIDTH // 5)
                    ren_width = rendered.get_width()
                    for j, line in enumerate(lines):
                        rendered = self.small_font.render(line, self.engine.antialias_text, WHITE)
                        self.screen.blit(rendered, (320 + ren_width + 20, y_offset + j*25))
                y_offset += 25
            
            # Equipment list (when selecting equipment to equip)
            available_text = self.font.render("Available Equipment:", self.engine.antialias_text, WHITE)
            self.screen.blit(available_text, (20, 300))
            
            current_slot = list(EquipmentSlot)[selected_slot]
            available_equipment = [eq for eq in party.inventory 
                                    if eq.slot == current_slot]
            
            for i, equipment in enumerate(available_equipment):
                color = YELLOW if i == selected_equipment and show_equipment_list else WHITE
                eq_text = equipment.name
                if equipment.slot == EquipmentSlot.WEAPON:
                    eq_text += f" (Power: {equipment.power})"
                elif equipment.slot == EquipmentSlot.ARMOR:
                    eq_text += f" (Guard: {equipment.guard})"
                
                rendered = self.small_font.render(eq_text, True, color)
                self.screen.blit(rendered, (40, 330 + i * 25))
            
            if not available_equipment:
                no_eq_text = self.small_font.render("No equipment available for this slot", True, GRAY)
                self.screen.blit(no_eq_text, (40, 330))
        
        # Instructions
        instructions = [
            "1-8: Select character",
            "UP/DOWN: Navigate slots",
            "ENTER: Select equipment",
            "BACKSPACE: Select slot",
            "U: Unequip item",
            "ESC: Return"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, GRAY)
            self.screen.blit(text, (20, SCREEN_HEIGHT - 120 + i * 20))
    
    def render_options_menu(self):
        options = self.engine.options
        selected_option = self.engine.selected_option
        self.screen.fill(BLACK)
        
        title = self.font.render("OPTIONS", self.engine.antialias_text, WHITE)
        self.screen.blit(title, (20, 20))
        
        option_texts = [
            f"Music Volume: {int(options.music_volume * 100)}%",
            f"Sound Volume: {int(options.sound_volume * 100)}%", 
            f"Fullscreen: {'ON' if options.fullscreen else 'OFF'}",
            f"Show Grid: {'ON' if options.show_grid else 'OFF'}",
            f"Auto Save: {'ON' if options.auto_save else 'OFF'}",
            "Save Options",
            "Return"
        ]
        
        for i, text in enumerate(option_texts):
            color = YELLOW if i == selected_option else WHITE
            rendered = self.font.render(text, True, color)
            self.screen.blit(rendered, (40, 80 + i * 40))
        
        # Instructions
        instructions = [
            "Use UP/DOWN arrows to navigate",
            "LEFT/RIGHT to change values",
            "ENTER to select"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, GRAY)
            self.screen.blit(text, (20, SCREEN_HEIGHT - 80 + i * 20))

    def render_quest_log(self):
        quest_log = self.engine.quest_log
        selected_indices = self.engine.selected_quest_indices
        current_focus = self.engine.current_quest_focus
        self.screen.fill((0, 0, 0))  # Clear screen
        mid_x = SCREEN_WIDTH // 2
        mid_y = SCREEN_HEIGHT // 2
        focus_colors = [YELLOW, MAGENTA, CYAN]
        quests = [q for q in quest_log.quests.values() if q.started]
        selected_quest = quests[selected_indices[0]]
        def quest_bit(label: str, label_pos: tuple[int, int], i: int, x_end: int, quest_stuff: list[QuestStep]):
            text = self.get_cached_text(label, self.large_font, WHITE)
            self.screen.blit(text, label_pos)
            y = text.get_height() + label_pos[1]
            for j, quest in enumerate(quest_stuff):
                if not quest.started:
                    continue
                color = self._get_status_color(quest)
                if current_focus == i and j == selected_indices[i]:
                    color = focus_colors[i]
                text = self.get_cached_text(quest.name, self.large_font, color)
                self.screen.blit(text, (label_pos[0], y))
                y += text.get_height() + 10
                # Show description below if selected
                if current_focus == i and j == selected_indices[i]:
                    desc_lines = self._wrap_text(quest.description, self.font, x_end)
                    for line in desc_lines:
                        desc = self.get_cached_text(line, self.font, (200, 200, 200))
                        self.screen.blit(desc, (label_pos[0], y))
                        y += desc.get_height()
        # ---- LEFT: Quest Names ----
        quest_bit("Quests", (20, 20), 0, mid_x - 40, quests)
        # ---- UPPER RIGHT: Quest Steps ----
        steps = list(selected_quest.steps.values()) if quests else []
        quest_bit("Quest Steps", (mid_x + 20, 20), 1, mid_x - 40, steps)
        # ---- LOWER RIGHT: Quest Hints ----
        hints = list(selected_quest.hints.values()) if quests else []
        quest_bit("Quest Notes", (mid_x + 20, mid_y + 20), 2, mid_x - 40, hints)

    def _get_status_color(self, obj):
        if getattr(obj, "failed", False):
            return RED
        elif getattr(obj, "completed", False):
            return GREEN
        elif getattr(obj, "started", False):
            return WHITE
        return (100, 100, 100)

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int):
        """Utility to wrap text into lines fitting max_width."""
        words = text.split()
        lines, line = [], ""
        for word in words:
            if word == "--n":
                lines.append(line)
                line = ""
                continue
            test = f"{line} {word}".strip()
            
            if font.size(test)[0] <= max_width:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines
    
    def render_save_load_menu(self, save_files: List[str]):
        selected_file = self.engine.selected_save
        is_save_mode = self.engine.is_save_mode
        self.screen.fill(BLACK)
        
        title = self.font.render("SAVE GAME" if is_save_mode else "LOAD GAME", self.engine.antialias_text, WHITE)
        self.screen.blit(title, (20, 20))
        
        if not save_files and not is_save_mode:
            no_saves_text = self.font.render("No save files found", True, GRAY)
            self.screen.blit(no_saves_text, (40, 80))
        else:
            if is_save_mode:
                new_save_text = "NEW SAVE"
                color = YELLOW if selected_file == 0 else WHITE
                rendered = self.font.render(new_save_text, True, color)
                self.screen.blit(rendered, (40, 80))
                
                start_index = 1
            else:
                start_index = 0
            
            for i, filename in enumerate(save_files):
                color = YELLOW if i + start_index == selected_file else WHITE
                rendered = self.font.render(filename, True, color)
                self.screen.blit(rendered, (40, 80 + (i + start_index) * 30))
        
        # Instructions
        instructions = [
            "Use UP/DOWN arrows to navigate",
            "ENTER to select",
            "ESC to return"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, GRAY)
            self.screen.blit(text, (20, SCREEN_HEIGHT - 80 + i * 20))
    
    def draw_text_with_outline(self, text, font, x, y, text_color, outline_color=BLACK):
        """Draw text with a black outline for better visibility."""
        base = self.get_cached_text(text, font, text_color)
        outline = self.get_cached_text(text, font, outline_color)
        
        # Draw outline by rendering text offset in each direction
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    self.screen.blit(outline, (x + dx, y + dy))
        
        # Draw actual text on top
        self.screen.blit(base, (x, y))
        return base.get_width(), base.get_height()

    def render_dialog(self):
        dialog_manager = self.engine.dialog_manager
        # Render current dialog line
        current_line = dialog_manager.current_line
        # Get speaker name
        speaker_name = ""
        if "__" in current_line:
            speaker_name, current_line = current_line.split("__")
        elif dialog_manager.current_speaker:
            try:
                speaker_name = dialog_manager.current_speaker.args.get("name", "NPC")
            except AttributeError:
                speaker_name = dialog_manager.current_speaker.name

        dialog_rect = self.render_bottom_text_box(speaker_name, current_line)

        # Show input area if awaiting input
        if dialog_manager.awaiting_keyword:
            input_y = dialog_rect.y + dialog_rect.height - 40
            input_rect = pygame.Rect(dialog_rect.x + 10, input_y, dialog_rect.width - 20, 30)
            pygame.draw.rect(self.screen, (20, 20, 40), input_rect)
            pygame.draw.rect(self.screen, WHITE, input_rect, 1)
            
            # Render user input
            if dialog_manager.user_input:
                input_text = self.font.render(dialog_manager.user_input, self.engine.antialias_text, WHITE)
            else:
                input_text = self.font.render("Type your response keyword here.", self.engine.antialias_text, GRAY)
            self.screen.blit(input_text, (input_rect.x + 5, input_rect.y))
            
            # Render blinking cursor
            dialog_manager.cursor_blink += 1
            if dialog_manager.cursor_blink % 60 < 30:  # Blink every second
                cursor_x = input_rect.x + 5 + self.font.size(dialog_manager.user_input)[0]
                pygame.draw.line(self.screen, WHITE, 
                               (cursor_x, input_rect.y + 3), 
                               (cursor_x, input_rect.y + input_rect.height - 3), 2)
        else:
            # Show "Press SPACE to continue" message
            if "(Y/N)" in current_line:
                continue_text = self.get_cached_text("Press 'Y' for yes or 'N' for no...", self.small_font, GRAY)
            else:
                continue_text = self.get_cached_text("Press SPACE to continue...", self.small_font, GRAY)
            self.screen.blit(continue_text, (dialog_rect.x + 10, dialog_rect.y + dialog_rect.height - 25))
    def render_debug(self):
        dialog_manager = self.engine.dialog_manager
        dialog_rect = self.render_bottom_text_box("Debug Input", "")
        input_y = dialog_rect.y + dialog_rect.height - 35
        input_rect = pygame.Rect(dialog_rect.x + 10, input_y, dialog_rect.width - 20, 25)
        pygame.draw.rect(self.screen, (20, 20, 40), input_rect)
        pygame.draw.rect(self.screen, WHITE, input_rect, 1)
        
        # Render user input
        input_text = self.font.render(dialog_manager.user_input, self.engine.antialias_text, WHITE)
        self.screen.blit(input_text, (input_rect.x + 5, input_rect.y + 3))
        
        # Render blinking cursor
        dialog_manager.cursor_blink += 1
        if dialog_manager.cursor_blink % 60 < 30:  # Blink every second
            cursor_x = input_rect.x + 5 + self.font.size(dialog_manager.user_input)[0]
            pygame.draw.line(self.screen, WHITE, 
                            (cursor_x, input_rect.y + 3), 
                            (cursor_x, input_rect.y + input_rect.height - 3), 2)
    def render_event_dialog(self):
        event_manager = self.engine.event_manager
        try:
            speaker_name = event_manager.speaker_name
        except AttributeError:
            return
        current_line = event_manager.current_line
        dialog_rect = self.render_bottom_text_box(speaker_name, current_line)
        # Show "Press SPACE to continue" message
        if "(Y/N)" in current_line:
            continue_text = self.get_cached_text("Press 'Y' for yes or 'N' for no...", self.small_font, GRAY)
        else:
            continue_text = self.get_cached_text("Press SPACE to continue...", self.small_font, GRAY)
        self.screen.blit(continue_text, (dialog_rect.x + 10, dialog_rect.y + dialog_rect.height - 25))

    def render_combat_log(self):
        if not self.engine.state == GameState.COMBAT:
            return
        combat_log = self.engine.combat_manager.combat_log
        combat_scroll_index = self.engine.combat_manager.combat_scroll_index
        big_line = ""
        for i in range(5):
            big_line += " --n " + combat_log[combat_scroll_index + i]
        self.render_bottom_text_box( "Combat Log", big_line)
        
        
    #@time_function("Render Text Box: ")
    def render_bottom_text_box(self, speaker_name: str = "", current_line: str = "", dialog_width = MAP_VIEW_WIDTH):
        """Render the dialog interface"""
        # Create dialog box
        dialog_height = SCREEN_HEIGHT - MAP_VIEW_HEIGHT 
        dialog_y = SCREEN_HEIGHT - dialog_height
        dialog_rect = pygame.Rect(0, dialog_y, dialog_width, dialog_height)
        
        # Draw dialog box background
        pygame.draw.rect(self.screen, (40, 40, 60), dialog_rect)
        pygame.draw.rect(self.screen, WHITE, dialog_rect, 2)
        if self.engine.state in [GameState.TOWN]:
            current_line = ""
            for i in range(5):
                current_line += " --n " + self.engine.messages[i]
        if self.engine.state in [GameState.EVENT, GameState.DIALOG, GameState.TOWN, GameState.COMBAT, GameState.CUTSCENE]:
            # Render speaker name
            if speaker_name:
                self.draw_text_with_outline(f"{speaker_name}:", self.font, dialog_rect.x + 10, dialog_rect.y + 10, YELLOW)
            if current_line:
                
                lines = self._wrap_text(current_line, self.font, dialog_rect.width - 40)
                
                # Render wrapped lines
                for i, line in enumerate(lines):
                    x = dialog_rect.x + 10
                    y = dialog_rect.y + 40 + i * 25
                    words = line.split(' ')
                    line_part = ""
                    for word in words:
                        color = WHITE
                        # Check for asterisk-wrapped word
                        split_word = word.split("*")
                        if len(split_word) == 3:
                            line_part += (" " + split_word[0])
                            self.draw_text_with_outline(line_part, self.font, x, y, color)
                            x += self.font.size(line_part)[0]
                            self.draw_text_with_outline(split_word[1], self.font, x, y, RED)
                            x += self.font.size(split_word[1])[0]
                            line_part = split_word[2]
                        else:
                            line_part += (" " + word)

                    self.draw_text_with_outline(line_part, self.font, x, y, color)
        return dialog_rect
    
    def get_cached_text(self, text, font: pygame.font.Font, color):
        key = (text, font, color)
        if key not in self.text_cache:
            self.text_cache[key] = font.render(text, True, color)
        return self.text_cache[key]
    
    #@time_function("Render Sidebar: ")
    def render_sidebar_stats(self):
        party = self.engine.party
        sidebar_width = SCREEN_WIDTH - MAP_VIEW_WIDTH 
        sidebar_x = SCREEN_WIDTH - sidebar_width
        sidebar_rect = pygame.Rect(sidebar_x, 0, sidebar_width, SCREEN_HEIGHT)
        other_rect = pygame.Rect(0, MAP_VIEW_HEIGHT, MAP_VIEW_WIDTH, SCREEN_HEIGHT - MAP_VIEW_HEIGHT)
        
        # Draw dialog box background
        pygame.draw.rect(self.screen, (40, 40, 60), sidebar_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), other_rect)
        pygame.draw.rect(self.screen, WHITE, sidebar_rect, 2)
        side_font_height = self.side_font.get_height()
        colors = [WHITE, RED, BLUE, YELLOW, (255, 0, 255), (0, 255, 255), (255, 128, 0), (128, 255, 0)]
        for i, character in enumerate(party.members):
            rendered = self.get_cached_text(f"{character.name}: Lvl-{character.level}", self.side_font, WHITE)
            self.screen.blit(rendered, (MAP_VIEW_WIDTH + 10, 50*i + TILE_HEIGHT))
            rendered = self.get_cached_text(f"HP: {character.hp}/{character.max_hp}", self.side_font, WHITE)
            self.screen.blit(rendered, (MAP_VIEW_WIDTH + 10, side_font_height + 2 + 50*i + TILE_HEIGHT))
            virtue_penalty_text = ""
            for type, virtue in character.virtue_manager.virtues.items():
                if virtue["overuse"]:
                    virtue_penalty_text += f"{type.value[0].capitalize()}: {virtue["overuse"]}/{character.virtue_manager.get_threshold(type)} "
            if virtue_penalty_text:
                rendered = self.get_cached_text(virtue_penalty_text, self.side_font, WHITE)
                self.screen.blit(rendered, (MAP_VIEW_WIDTH + 10, 2*side_font_height + 2 + 50*i + TILE_HEIGHT))
            if character.image:
                self.screen.blit(character.image, (SCREEN_WIDTH - TILE_WIDTH, 20 + 50*i + TILE_HEIGHT))
        rendered = self.get_cached_text(f"{self.engine.schedule_manager.current_game_time}", self.side_font, WHITE)
        self.screen.blit(rendered, (MAP_VIEW_WIDTH + 10, 20 + 4*side_font_height + (len(self.engine.party.members)+1)*TILE_HEIGHT))


    def render_cutscene(self):
        cutscene_manager = self.engine.cutscene_manager
        if cutscene_manager.current_image:
            self.screen.blit(cutscene_manager.current_image, (0, 0))
        current_line = cutscene_manager.get_current_line()
        cutscene_textbox_rect = self.render_bottom_text_box("", current_line, SCREEN_WIDTH)
            
        # Show "Press SPACE to continue" message
        continue_text = self.small_font.render("Press SPACE to continue, or ENTER to SKIP...", True, GRAY)
        self.screen.blit(continue_text, (cutscene_textbox_rect.x + 10, cutscene_textbox_rect.y + cutscene_textbox_rect.height - 25))


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

    def get_visible_positions(self, observer_pos, max_distance=3) -> set:
        """
        Perimeter raycast FOV:
        - cast one Bresenham ray to every tile on the perimeter of the square/circle of radius `max_distance`
        - walk the ray; every tile visited is visible. stop the ray when an opaque tile is hit.
        Caches last result and only recomputes when observer moves or map changes.
        """

        # Basic cache keys -- you should increment current_map.generation (or similar) whenever
        # an opaque tile changes, doors open/close, etc. If you don't have this, you can
        # detect map object identity but that won't notice internal changes.
        game_map = self.engine.current_map
        map_gen = getattr(game_map, "generation", None)  # preferred: an integer you increment on map change

        # Fast cache check
        if not self._fov_cache:
            self._fov_cache = {}
        cache_key = (observer_pos, max_distance, id(game_map), map_gen)
        if cache_key == self._fov_cache_key:
            return self._fov_cache  # cached set

        ox, oy = observer_pos
        visible = set()
        visible.add((ox, oy))

        radius = int(max_distance)
        # Precompute perimeter points: use square perimeter but treat distance check so you still get near-circle
        # We'll walk all points on the bounding square perimeter to ensure cardinals and diagonals are covered.
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
        map_w = game_map.width
        map_h = game_map.height

        for tx, ty in perim:
            for x, y in self._bresenham_line(ox, oy, tx, ty):
                if ox == x and oy == y:
                    continue
                if x < 0 or y < 0 or x >= map_w or y >= map_h:
                    break

                visible.add((x, y))

                if not game_map.can_see_thru((x, y)):
                    # include the blocking tile (we can see it) but stop further tiles along this ray
                    break

        # Save cache
        self._fov_cache = visible
        self._fov_cache_key = cache_key

        return visible
    def get_rectangle(self, w0_factor: int = 1, h0_factor: int = 1, w1_factor: int = 1, h1_factor: int = 1, color_rect0: tuple[int, int, int] = WHITE, color_rect1: tuple[int, int, int] = BLACK):
        rect = pygame.Rect(SCREEN_WIDTH // w0_factor, SCREEN_HEIGHT // h0_factor, SCREEN_WIDTH // w1_factor, SCREEN_HEIGHT // h1_factor)
        pygame.draw.rect(self.screen, color_rect0, rect)
        pygame.draw.rect(self.screen, color_rect1, rect, 2)
        return rect
    
    def draw_background(self):
        """Draw the store background"""
        self.screen.fill(DARK_GRAY)
        
        # Draw store title
        title = self.get_cached_text("Merchant's Store", self.large_font, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT//25))
        self.screen.blit(title, title_rect)
        
        # Draw gold display
        self.draw_text_with_outline(f"Gold: {self.engine.party.gold}", self.small_font, 20, 20, GOLD)
    def draw_mode_buttons(self):
        """Draw buy/sell mode buttons"""
        buy_color = GREEN if self.engine.merchant.mode == "buy" else GRAY
        sell_color = RED if self.engine.merchant.mode == "sell" else GRAY
        
        # Buy button
        buy_text = self.get_cached_text("BUY", self.side_font, BLACK)
        buy_rect = pygame.Rect(SCREEN_WIDTH // 24, SCREEN_HEIGHT // 10, SCREEN_WIDTH // 12, SCREEN_HEIGHT // 20)
        pygame.draw.rect(self.screen, buy_color, buy_rect)
        pygame.draw.rect(self.screen, BLACK, buy_rect, 2)
        buy_text_rect = buy_text.get_rect(center=buy_rect.center)
        self.screen.blit(buy_text, buy_text_rect)
        
        # Sell button
        
        sell_text = self.get_cached_text("SELL", self.side_font, BLACK)
        sell_rect = pygame.Rect(SCREEN_WIDTH // 7, SCREEN_HEIGHT // 10, SCREEN_WIDTH // 12, SCREEN_HEIGHT // 20)
        pygame.draw.rect(self.screen, sell_color, sell_rect)
        pygame.draw.rect(self.screen, BLACK, sell_rect, 2)
        sell_text_rect = sell_text.get_rect(center=sell_rect.center)
        self.screen.blit(sell_text, sell_text_rect)
        
        return buy_rect, sell_rect
    
    def draw_category_buttons(self):
        """Draw category filter buttons"""
        button_width = self.get_cached_text(self.engine.merchant.longest_category, self.small_font, LIGHT_GRAY).get_width() + SCREEN_WIDTH // 80
        button_height = SCREEN_HEIGHT // 20
        start_x = SCREEN_WIDTH // 24
        start_y = SCREEN_HEIGHT // 6
        
        category_rects = []
        
        for i, cat in enumerate(self.engine.merchant.categories):#Unroll these later
            x = start_x + (i * (button_width + 5))
            if x + button_width > 3*SCREEN_WIDTH // 4:  # Leave space for party view
                break
                
            rect = pygame.Rect(x, start_y, button_width, button_height)
            color = BLUE if self.engine.merchant.category == cat else LIGHT_GRAY
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 1)
            
            text_color = WHITE if self.engine.merchant.category == cat else BLACK
            cat_text = self.get_cached_text(cat.upper(), self.small_font, text_color)
            text_rect = cat_text.get_rect(center=rect.center)
            self.screen.blit(cat_text, text_rect)
            
            category_rects.append((rect, cat))
        
        return category_rects
    
    def draw_party_selection(self):
        
        party_rect = pygame.Rect(8*SCREEN_WIDTH//11, SCREEN_HEIGHT // 80, 23*SCREEN_WIDTH//88, 39*SCREEN_HEIGHT // 40)
        pygame.draw.rect(self.screen, WHITE, party_rect)
        pygame.draw.rect(self.screen, BLACK, party_rect, 2)
        
        # Title
        title_text = self.get_cached_text("Party Members", self.side_font, BLACK)
        self.screen.blit(title_text, (party_rect.x + (party_rect.width - title_text.get_width())//2, party_rect.y + SCREEN_HEIGHT//108))
        
        member_rects = []
        
        # Draw 2 members per row
        for i, member in enumerate(self.engine.party.members):
            row = i // 2
            col = i % 2
            
            x = party_rect.x + party_rect.width/32 + + col * (2*TILE_WIDTH + SCREEN_WIDTH // 13)
            y = party_rect.y + title_text.get_height() + SCREEN_HEIGHT//108 + row * (2*TILE_HEIGHT + SCREEN_HEIGHT // 7 + 7)
            
            member_rect = pygame.Rect(x, y, 2*TILE_WIDTH + SCREEN_WIDTH // 16, 2*TILE_HEIGHT + SCREEN_HEIGHT // 7)
            
            pygame.draw.rect(self.screen, LIGHT_GRAY, member_rect)
            pygame.draw.rect(self.screen, BLACK, member_rect, 1)
            
            # Member name
            name_text = self.get_cached_text(member.name, self.small_font, BLACK)
            name_rect = name_text.get_rect(center=(member_rect.centerx, member_rect.y + 10))
            self.screen.blit(name_text, name_rect)
            
            # Current equipment in slot
            selected_item = self.engine.merchant.selected_item
            slot_key = selected_item.slot.value if selected_item.slot else None
            current_item = member.equipped.get(slot_key) if slot_key else None
            def compare_stats_for_equipment(current_stat, new_stat, text_shorthand, y_offset):
                text_width, _ = self.draw_text_with_outline(f"{text_shorthand}:{current_stat}", self.small_font, member_rect.x + 2, member_rect.bottom - y_offset, BLACK)
                if current_stat == new_stat:
                    return
                compare_color = RED if new_stat < current_stat else GREEN
                self.draw_text_with_outline(f"-> {new_stat} ({new_stat-current_stat})", self.small_font, member_rect.x + 2 + text_width, member_rect.bottom - y_offset, compare_color)
                
            
            # Current stats
            current_max_hp = member.get_max_hp()
            current_power = member.get_total_power()
            current_guard = member.get_total_guard()
            
            # Calculate new stats if item were equipped
            new_max_hp = current_max_hp - (current_item.max_hp if current_item else 0) + selected_item.max_hp
            new_power = current_power - (current_item.power if current_item else 0) + selected_item.power
            new_guard = current_guard - (current_item.guard if current_item else 0) + selected_item.guard
            compare_stats_for_equipment(current_max_hp, new_max_hp, "HP", 45)
            compare_stats_for_equipment(current_power, new_power, "POW", 30)
            compare_stats_for_equipment(current_guard, new_guard, "GRD", 15)

            member_rects.append((member_rect, i))
        
        return member_rects
    
    def draw_item_list(self):
        """Draw the list of items"""
        items = self.engine.merchant.get_filtered_items()
        
        # Calculate visible items based on scroll
        start_index = self.engine.merchant.start_index
        end_index = min(start_index + self.engine.merchant.items_per_page, len(self.engine.merchant.store_items))
        
        y_start = 9*SCREEN_HEIGHT//40
        item_rects = []
        
        for i, item in enumerate(items[start_index:end_index]):
            y_pos = y_start + i * self.engine.merchant.item_height
            
            list_width = int(1.1*self.side_font.size(item.name)[0])
            
            # Item background
            item_rect = pygame.Rect(SCREEN_WIDTH//24, y_pos, list_width, self.engine.merchant.item_height - SCREEN_HEIGHT//160)
            color = LIGHT_GRAY if item == self.engine.merchant.selected_item else WHITE
            pygame.draw.rect(self.screen, color, item_rect)
            pygame.draw.rect(self.screen, BLACK, item_rect, 2)
            
            # Item info
            name_text = self.get_cached_text(item.name, self.side_font, BLACK)
            name_rect = name_text.get_rect(left=item_rect.x+SCREEN_WIDTH//120, centery=item_rect.centery)
            self.draw_text_with_outline(item.name, self.side_font, name_rect.x, name_rect.y, BLACK)
            #Quantity Info
            qty_text = self.get_cached_text(f"x{item.quantity}", self.side_font, BLUE)
            qty_rect = qty_text.get_rect(left = item_rect.right + SCREEN_WIDTH//120, centery=item_rect.centery)
            self.draw_text_with_outline(f"x{item.quantity}", self.side_font, qty_rect.x, qty_rect.y, BLUE)
            
            # Price and quantity
            price_text = self.get_cached_text(f"${item.value}", self.side_font, GOLD)
            price_rect = price_text.get_rect(left=qty_rect.right + SCREEN_WIDTH//120, centery=qty_rect.centery)
            self.draw_text_with_outline(f"${item.value}", self.side_font, price_rect.x, price_rect.y, GOLD)
            
            item_rects.append((item_rect, item))
        
        return item_rects
    
    def draw_action_buttons(self):
        """Draw buy/sell action buttons"""
        if not self.engine.merchant.selected_item:
            return []
        
        button_y = SCREEN_HEIGHT - 80
        
        if self.engine.merchant.mode == "buy":
            # Check if player can afford
            can_afford = self.engine.party.gold >= self.engine.merchant.selected_item.value
            buy_color = GREEN if can_afford else GRAY
            
            buy_rect = pygame.Rect(50, button_y, 300, 40)
            pygame.draw.rect(self.screen, buy_color, buy_rect)
            pygame.draw.rect(self.screen, BLACK, buy_rect, 2)
            
            buy_text = self.get_cached_text("Press Enter to Buy Item", self.side_font, BLACK)
            buy_text_rect = buy_text.get_rect(center=buy_rect.center)
            self.screen.blit(buy_text, buy_text_rect)
            
            return [buy_rect] if can_afford else []
        
        else:  # sell mode
            if not self.engine.merchant.selected_item.can_be_sold:
                return []
            
            sell_rect = pygame.Rect(50, button_y, 120, 40)
            pygame.draw.rect(self.screen, RED, sell_rect)
            pygame.draw.rect(self.screen, BLACK, sell_rect, 2)
            
            sell_text = self.get_cached_text("SELL ITEM", self.side_font, BLACK)
            sell_text_rect = sell_text.get_rect(center=sell_rect.center)
            self.screen.blit(sell_text, sell_text_rect)
            
            return [sell_rect]
    #Screen transitions////////////
    #@time_function("Render Fade: ")
    def fade_render(self):
        if self.fading:
            if self.alpha_change_rate == 0:
                self.fading = False
            else:
                self.alpha += self.alpha_change_rate
                if self.alpha < 0 or self.alpha > 255:
                    self.fading = False
        if self.alpha > 0:
            self.veil.set_alpha(self.alpha)
            self.screen.blit(self.veil, (0, 0))