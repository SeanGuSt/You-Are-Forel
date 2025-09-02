from typing import TYPE_CHECKING
import pygame
from constants import GameState, DEFAULT_PLAYER_MOVE_FRAMES, DEFAULT_WAIT_PENALTY
from objects.object_templates import NPC, MapObject, Chest

if TYPE_CHECKING:
    from ultimalike import GameEngine

def debug_inputs(self: 'GameEngine', event):
    mods = pygame.key.get_mods()
    if mods & pygame.KMOD_CTRL:
        match event.key:
            case pygame.K_d:
                self.dialog_manager.load_dialogs()
            case pygame.K_e:
                self.event_manager.load_event_scripts()
    elif event.key == pygame.K_ESCAPE:
        self.dialog_manager.user_input = ""
        self.change_state(GameState.TOWN)
    elif event.key == pygame.K_BACKSPACE:
        if len(self.dialog_manager.user_input) > 0:
            self.dialog_manager.user_input = self.dialog_manager.user_input[:-1]
    elif event.key == pygame.K_RETURN:
        if "=" not in self.dialog_manager.user_input:
            self.dialog_manager.user_input += "="
        try:
            self.event_manager._do_event(self.dialog_manager.user_input)
            self.dialog_manager.user_input = ""
            self.change_state(GameState.TOWN)
        except Exception as e:
            self.append_to_message_log(f"{self.dialog_manager.user_input} is not a valid event because {e}.")
            self.dialog_manager.user_input = ""
            self.change_state(GameState.TOWN)

    elif event.unicode.isprintable() and len(self.dialog_manager.user_input) < 50:
        self.dialog_manager.user_input += event.unicode 
