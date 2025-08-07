from typing import TYPE_CHECKING
import pygame
from constants import GameState

if TYPE_CHECKING:
    from ultimalike import GameEngine
    
def dialog_inputs(self: 'GameEngine', event):
    match event.key:
        case pygame.K_ESCAPE:
            # Exit dialog
            self.dialog_manager.end_dialog()
            self.revert_state()
        case pygame.K_RETURN:
            if self.spell_input_mode:
                self.spell_input_mode = False
                spell = self.spellbook.process_user_input(self.dialog_manager.user_input)
                self.dialog_manager.user_input = ""
                self.dialog_manager.awaiting_input = False
                if self.previous_state == GameState.COMBAT:
                    caster = self.combat_manager.get_current_unit()
                else:
                    caster = self.party.get_leader()
                caster.prep_spell(spell)
            if self.dialog_manager.awaiting_input:
                # Process user input
                user_input = self.dialog_manager.process_user_input()
                if user_input == "bye":
                    self.dialog_manager.end_dialog()
                    self.revert_state()
            elif self.dialog_manager.looking:
                if not self.dialog_manager.advance_looking():
                    self.dialog_manager.end_dialog()
                    self.revert_state()
        case pygame.K_SPACE:
            # Advance dialog
            if not self.dialog_manager.awaiting_input:
                if self.dialog_manager.looking:
                    if not self.dialog_manager.advance_looking():
                        self.dialog_manager.end_dialog()
                        self.revert_state()
                elif not self.dialog_manager.advance_dialog():
                    # Dialog finished advancing, now awaiting input
                    if self.event_manager.force_end:
                        self.dialog_manager.end_dialog()
                        self.revert_state()
    if self.dialog_manager.awaiting_input:
        # Handle text input for dialog responses
        if event.key == pygame.K_BACKSPACE:
            self.dialog_manager.user_input = self.dialog_manager.user_input[:-1]
        elif event.key == pygame.K_SPACE and len(self.dialog_manager.user_input) == 0:
            pass
        elif event.unicode.isprintable() and len(self.dialog_manager.user_input) < 50:
            self.dialog_manager.user_input += event.unicode 
            if self.dialog_manager.user_input in ["nigge", "faggo", "rapis", "chink"]:
                self.running = False