from typing import TYPE_CHECKING
import pygame
from save_manager import SaveManager
from constants import GameState

if TYPE_CHECKING:
    from ultimalike import GameEngine

def main_menu_inputs(self: 'GameEngine', event):
    match event.key:
        case pygame.K_n:
            self.start_new_game()
        case pygame.K_l:
            self.change_state(GameState.MENU_SAVE_LOAD)
            self.is_save_mode = False
            self.selected_save = 0
        case pygame.K_o:
            self.change_state(GameState.MENU_OPTIONS)
            self.selected_option = 0
        case pygame.K_q:
            self.running = False

def options_menu_inputs(self: 'GameEngine', event):
    match event.key:
        case pygame.K_ESCAPE:
            self.revert_state()
        case pygame.K_UP | pygame.K_DOWN | pygame.K_LEFT | pygame.K_RIGHT:
            dx, dy = self.get_direction(event.key).value
            self.selected_option = (self.selected_option + dy) % 7
            self.adjust_option(dx)
        case pygame.K_RETURN:
            if self.selected_option == 5:  # Save Options
                self.save_options()
            elif self.selected_option == 6:  # Return
                self.revert_state()

def save_load_inputs(self: 'GameEngine', event):
    match event.key:
        case pygame.K_ESCAPE:
            self.state = GameState.MAIN_MENU if self.party is None else self.previous_state
        case pygame.K_UP | pygame.K_DOWN:
            dx, dy = self.get_direction(event.key).value
            save_files = SaveManager.get_save_files()
            max_index = len(save_files) + (1 if self.is_save_mode else 0)
            self.selected_save = (self.selected_save + dy) % max_index
        case pygame.K_RETURN:
            self.handle_save_load_selection()