from typing import TYPE_CHECKING
import pygame
from constants import GameState

if TYPE_CHECKING:
    from ultimalike import GameEngine
    
def events_inputs(self: 'GameEngine', event):
    match event.key:
        case pygame.K_SPACE:
            if not self.event_manager.yesno_question:
                self.event_manager.waiting_for_input = False
        case pygame.K_y:
            if self.event_manager.yesno_question and self.event_manager.waiting_for_input:
                self.event_manager.yesno_question = 0
                self.event_manager.waiting_for_input = False
        case pygame.K_n:
            if self.event_manager.yesno_question and self.event_manager.waiting_for_input:
                self.event_manager.current_index += self.event_manager.yesno_question
                self.event_manager.yesno_question = 0
                self.event_manager.waiting_for_input = False