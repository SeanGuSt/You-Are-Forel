from typing import TYPE_CHECKING
import pygame
from constants import GameState

if TYPE_CHECKING:
    from ultimalike import GameEngine
    
def dialog_inputs(self: 'GameEngine', event):
    match event.key:
        case pygame.K_RETURN:
            if self.spell_input_mode:
                self.spell_input_mode = False
                spell = self.spellbook.process_user_input(self.dialog_manager.user_input)
                self.dialog_manager.user_input = ""
                self.dialog_manager.awaiting_keyword = False
                self.dialog_manager.waiting_for_input = False
                if self.previous_state == GameState.COMBAT:
                    caster = self.combat_manager.get_current_unit()
                else:
                    caster = self.party.get_leader()
                caster.prep_spell(spell)
            if self.dialog_manager.awaiting_keyword:
                # Process user input
                user_input = self.dialog_manager.process_user_input()
        case pygame.K_SPACE:
            # Advance dialog
            if not self.dialog_manager.awaiting_keyword:
                self.dialog_manager.waiting_for_input = False
    if self.dialog_manager.awaiting_keyword:
        # Handle text input for dialog responses
        if event.key == pygame.K_BACKSPACE:
            self.dialog_manager.user_input = self.dialog_manager.user_input[:-1]
        elif event.key == pygame.K_SPACE and len(self.dialog_manager.user_input) == 0:
            pass
        elif event.unicode.isprintable() and len(self.dialog_manager.user_input) < 50:
            self.dialog_manager.user_input += event.unicode 
            if self.dialog_manager.user_input in ["nigger", "faggot", "chink"]:
                self.running = False