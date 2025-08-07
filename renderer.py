import pygame
from typing import List, TYPE_CHECKING
from constants import *
from objects.characters import Party, Character
from dialog.dialog import DialogManager
from cutscenes import CutsceneManager
from objects.map_objects import Map, Node, NPC, Monster, ItemHolder, Teleporter, MapObject
from options import GameOptions
from combat import CombatManager

if TYPE_CHECKING:
    from ultimalike import GameEngine

class Renderer:
    def __init__(self, engine: 'GameEngine', screen):
        self.engine = engine
        self.screen = screen
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.SysFont("consolas", 18)
        self.large_font = pygame.font.SysFont("consolas", 30)
        self.side_font = pygame.font.SysFont("consolas", 20)
        self.text_cache: dict[tuple[str, pygame.font.Font, tuple[int, int, int]], pygame.Surface] = {}
        
        # Tile colors for simple rendering
        self.tile_colors = {
            TileType.GRASS: GREEN,
            TileType.WATER: BLUE,
            TileType.MOUNTAIN: GRAY,
            TileType.FOREST: (0, 128, 0),
            TileType.TOWN: YELLOW,
            TileType.DUNGEON: DARK_GRAY,
            TileType.FLOOR: (200, 180, 140),
            TileType.WALL: (100, 100, 100),
            TileType.DOOR: (139, 69, 19)
        }
    #@time_function("render map")
    def render_map(self):
        game_map = self.engine.current_map
        camera = self.engine.camera
        show_grid = self.engine.options.show_grid
        cam_x, cam_y = camera

        tile_offset_x = cam_x % 1  # fractional offset in tile
        tile_offset_y = cam_y % 1

        pixel_offset_x = tile_offset_x * TILE_WIDTH
        pixel_offset_y = tile_offset_y * TILE_HEIGHT

        base_tile_x = int(cam_x)
        base_tile_y = int(cam_y)

        for y in range(MAP_HEIGHT + 1):  # +1 to cover partial bottom row
            for x in range(MAP_WIDTH + 1):  # +1 to cover partial right column
                map_x = base_tile_x + x
                map_y = base_tile_y + y

                tile = game_map.get_tile_lower((map_x, map_y))
                screen_x = x * TILE_WIDTH - pixel_offset_x
                screen_y = y * TILE_HEIGHT - pixel_offset_y

                if tile:
                    if tile.image:
                        scaled_image = pygame.transform.scale(tile.image, (TILE_WIDTH, TILE_HEIGHT))
                        self.screen.blit(scaled_image, (screen_x, screen_y))
                    else:
                        rect = pygame.Rect(screen_x, screen_y, TILE_WIDTH, TILE_HEIGHT)
                        pygame.draw.rect(self.screen, tile.color, rect)

                    if show_grid:
                        pygame.draw.rect(self.screen, BLACK, rect, 1)
        def incremental_movement(timer_name: str, screen_x, screen_y, prevent_jittering: bool = False,):
            j = self.engine.event_manager.timers[timer_name]
            j_max = self.engine.event_manager.timer_limits[timer_name]
            dx, dy = obj.subtract_tuples(obj.position, obj.old_position)
            screen_x -= dx*(TILE_WIDTH - j*TILE_WIDTH//j_max)
            screen_y -= dy*(TILE_HEIGHT - j*TILE_HEIGHT//j_max)
            if j == j_max and prevent_jittering:
                obj.old_position = obj.position
            return screen_x, screen_y
        def bump_movement(screen_x, screen_y):
            """Handle bump animation - goes halfway out, then back"""
            j = self.engine.event_manager.timers["player_bump"]
            j_max = self.engine.event_manager.timer_limits["player_bump"]
            
            # Get bump direction from the character
            dx, dy = obj.bump_direction.value
            
            # Create a "bounce" effect - go out then come back
            if j <= j_max // 2:
                # First half: move toward the obstacle (halfway)
                progress = j / (j_max // 2)
                screen_x += dx * (TILE_WIDTH // 5) * progress
                screen_y += dy * (TILE_HEIGHT // 5) * progress
            else:
                # Second half: move back to original position
                progress = (j - j_max // 2) / (j_max // 2)
                screen_x += dx * (TILE_WIDTH // 5) * (1 - progress)
                screen_y += dy * (TILE_HEIGHT // 5) * (1 - progress)
            self.engine.event_manager.timers["player_bump"] += 1
            # Clean up when animation is complete
            if j >= j_max:
                obj.is_bumping = False
                obj.bump_direction = None
                self.engine.event_manager.timer_limits["player_bump"] = 0
                self.engine.event_manager.timers["player_bump"] = 0
            return screen_x, screen_y
        
        # Render map objects
        for obj in game_map.objects:
            obj.update()
            if type(obj) == Node:#No need to render nodes
                continue
            elif obj.__is__(Character):#If this is a party member other than the leader, don't render them outside of combat.
                if (not self.engine.state == GameState.COMBAT and not obj == self.engine.party.get_leader()):
                    continue
            map_x, map_y = obj.subtract_tuples(obj.position, camera)
            
            if -1 <= map_x <= MAP_WIDTH and -1 <= map_y <= MAP_HEIGHT:
                screen_x = map_x*TILE_WIDTH
                screen_y = map_y*TILE_HEIGHT
                if self.engine.event_manager.timer_limits["player_move"]:
                    screen_x, screen_y = incremental_movement("player_move", screen_x, screen_y, prevent_jittering=True)
                elif obj == self.engine.party.get_leader() and self.engine.event_manager.timer_limits["player_bump"]:
                    screen_x, screen_y = bump_movement(screen_x, screen_y)
                elif obj in self.engine.event_manager.walkers and self.engine.event_manager.timer_limits["event_wait"]:
                    screen_x, screen_y = incremental_movement("event_wait", screen_x, screen_y, True)
                elif obj in self.engine.event_manager.walkers and self.engine.event_manager.timer_limits["enemy_move"]:
                    screen_x, screen_y = incremental_movement("enemy_move", screen_x, screen_y)
                
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
        self.screen.fill(BLACK)
        
        title = self.font.render("INVENTORY", self.engine.antialias_text, WHITE)
        self.screen.blit(title, (20, 20))
        
        gold_text = self.font.render(f"Gold: {party.gold}", True, YELLOW)
        self.screen.blit(gold_text, (20, 50))
        
        y_offset = 90
        for item in party.inventory:
            item_text = self.small_font.render(f"{item.name} x{item.quantity}", self.engine.antialias_text, WHITE)
            desc_text = self.small_font.render(f"  {item.description}", True, GRAY)
            
            self.screen.blit(item_text, (20, y_offset))
            self.screen.blit(desc_text, (20, y_offset + 20))
            y_offset += 45
            
        # Instructions
        instruction = self.small_font.render("Press ESC to return", True, YELLOW)
        self.screen.blit(instruction, (20, SCREEN_HEIGHT - 30))
    
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
                color = YELLOW if i == selected_slot and not show_equipment_list else WHITE
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
                    lines = self._wrap_text(equipped_item.description, self.small_font, 240)
                    ren_width = rendered.get_width()
                    for j, line in enumerate(lines):
                        rendered = self.small_font.render(line, self.engine.antialias_text, WHITE)
                        self.screen.blit(rendered, (320 + ren_width + 20, y_offset + j*25))
                y_offset += 25
            
            # Equipment list (when selecting equipment to equip)
            if show_equipment_list:
                available_text = self.font.render("Available Equipment:", self.engine.antialias_text, WHITE)
                self.screen.blit(available_text, (20, 300))
                
                current_slot = list(EquipmentSlot)[selected_slot]
                available_equipment = [eq for eq in party.inventory 
                                     if eq.slot == current_slot]
                
                for i, equipment in enumerate(available_equipment):
                    color = YELLOW if i == selected_equipment else WHITE
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

        text = self.large_font.render("Quests", self.engine.antialias_text, WHITE)
        self.screen.blit(text, (20, 20))
        # ---- LEFT: Quest Names ----
        quests = [q for q in quest_log.quests.values() if q.started]
        quest_y = 40
        for i, quest in enumerate(quests):
            color = self._get_status_color(quest)
            if current_focus == 0 and i == selected_indices[0]:
                color = focus_colors[0]
            text = self.large_font.render(quest.name, True, color)
            self.screen.blit(text, (20, quest_y))
            quest_y += text.get_height() + 10

            # Show description below if selected
            if i == selected_indices[0]:
                desc_lines = self._wrap_text(quest.description, self.font, mid_x - 40)
                for line in desc_lines:
                    desc = self.font.render(line, True, (200, 200, 200))
                    self.screen.blit(desc, (20, quest_y))
                    quest_y += desc.get_height()

        # ---- UPPER RIGHT: Quest Steps ----
        text = self.large_font.render("Quest Steps", self.engine.antialias_text, WHITE)
        self.screen.blit(text, (mid_x + 20, 20))
        if quests:
            selected_quest = quests[selected_indices[0]]
            steps = list(selected_quest.steps.values())
            step_y = 40
            for i, step in enumerate(steps):
                if step.started:
                    color = self._get_status_color(step)
                    if current_focus == 1 and i == selected_indices[1]:
                        color = focus_colors[1]
                    text = self.font.render(step.name, True, color)
                    self.screen.blit(text, (mid_x + 20, step_y))
                    step_y += text.get_height() + 5

        # ---- LOWER RIGHT: Quest Hints ----
        text = self.large_font.render("Quest Hints", self.engine.antialias_text, WHITE)
        self.screen.blit(text, (mid_x + 20, mid_y + 20))
        hints = list(selected_quest.hints.values()) if quests else []
        hint_y = mid_y + 20
        for i, hint in enumerate(hints):
            color = self._get_status_color(hint)
            if current_focus == 2 and i == selected_indices[2]:
                color = focus_colors[2]
            text = self.font.render(hint.name, True, color)
            self.screen.blit(text, (mid_x + 20, hint_y))
            hint_y += text.get_height() + 5

    def _get_status_color(self, obj):
        if getattr(obj, "failed", False):
            return (255, 0, 0)
        elif getattr(obj, "completed", False):
            return (150, 150, 150)
        elif getattr(obj, "started", False):
            return (255, 255, 255)
        return (100, 100, 100)

    def _wrap_text(self, text, font, max_width):
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

    def render_dialog(self):
        dialog_manager = self.engine.dialog_manager
        # Render current dialog line
        current_line = dialog_manager.get_current_line()
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
        if dialog_manager.awaiting_input:
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
        else:
            # Show "Press SPACE to continue" message
            if "(Y/N)" in current_line:
                continue_text = self.get_cached_text("Press 'Y' for yes or 'N' for no...", self.small_font, GRAY)
            else:
                continue_text = self.get_cached_text("Press SPACE to continue...", self.small_font, GRAY)
            self.screen.blit(continue_text, (dialog_rect.x + 10, dialog_rect.y + dialog_rect.height - 25))

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
        
        
    
    def render_bottom_text_box(self, speaker_name: str = "", current_line: str = ""):
        """Render the dialog interface"""
        # Create dialog box
        dialog_height = SCREEN_HEIGHT - MAP_VIEW_HEIGHT 
        dialog_y = SCREEN_HEIGHT - dialog_height
        dialog_rect = pygame.Rect(0, dialog_y, SCREEN_WIDTH, dialog_height)
        
        # Draw dialog box background
        pygame.draw.rect(self.screen, (40, 40, 60), dialog_rect)
        pygame.draw.rect(self.screen, WHITE, dialog_rect, 2)

        # Render speaker name
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
            for type, virtue in character.virtue_manager.virtues.items():
                if virtue.overuse_points:
                    rendered = self.get_cached_text(f"{type.value}: {virtue.overuse_points}/{virtue.get_threshold()}", self.side_font, WHITE)
                    self.screen.blit(rendered, (MAP_VIEW_WIDTH + 10, 2*side_font_height + 2 + 50*i + TILE_HEIGHT))
            if character.image:
                self.screen.blit(character.image, (SCREEN_WIDTH - TILE_WIDTH, 20 + 50*i + TILE_HEIGHT))
        rendered = self.get_cached_text(f"{self.engine.schedule_manager.current_game_time}", self.side_font, WHITE)
        self.screen.blit(rendered, (MAP_VIEW_WIDTH + 10, 20 + 4*side_font_height + (len(self.engine.party.members)+1)*TILE_HEIGHT))


    def render_cutscene(self):
        cutscene_manager = self.engine.cutscene_manager
        current_line = cutscene_manager.get_current_line()
        cutscene_textbox_rect = self.render_bottom_text_box("", current_line)
            
        # Show "Press SPACE to continue" message
        continue_text = self.small_font.render("Press SPACE to continue, or ENTER to SKIP...", True, GRAY)
        self.screen.blit(continue_text, (cutscene_textbox_rect.x + 10, cutscene_textbox_rect.y + cutscene_textbox_rect.height - 25))

