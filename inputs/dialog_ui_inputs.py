from typing import TYPE_CHECKING
import pygame
from constants import GameState
from objects.npcs import ImedesInBed

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
                if self.state_stack[-2] == GameState.COMBAT:
                    caster = self.combat_manager.get_current_unit()
                else:
                    caster = self.party.get_leader()
                caster.prep_spell(spell)
            if self.dialog_manager.awaiting_keyword:
                # Process user input
                if self.dialog_manager.dialog_key == "imedes_in_bed" and self.dialog_manager.last_input == "yes":
                    if self.dialog_manager.user_input == "destroy":
                        user_input = self.dialog_manager.process_user_input()
                else:
                    user_input = self.dialog_manager.process_user_input()
        case pygame.K_SPACE:
            # Advance dialog
            if not self.dialog_manager.awaiting_keyword:
                self.dialog_manager.waiting_for_input = False
    if self.dialog_manager.awaiting_keyword:
        # Handle text input for dialog responses
        if self.dialog_manager.dialog_key == "imedes_in_bed" and self.dialog_manager.last_input == "yes":
            word = "destroy"
            if self.dialog_manager.scare_counter < len(word) and (event.key in [pygame.K_BACKSPACE, pygame.K_SPACE] or event.unicode.isprintable()):
                self.dialog_manager.user_input += word[self.dialog_manager.scare_counter]
                self.dialog_manager.scare_counter += 1

        elif event.key == pygame.K_BACKSPACE:
            self.dialog_manager.user_input = self.dialog_manager.user_input[:-1]
        elif event.key == pygame.K_SPACE and len(self.dialog_manager.user_input) == 0:
            pass
        elif event.unicode.isprintable() and len(self.dialog_manager.user_input) < 50:
            self.dialog_manager.user_input += event.unicode
            # Oh, sure, go ahead, use slurs. Let's see what that gets you. Aww, did your game crash? what a shame. 
            if self.dialog_manager.user_input in ["nigger", "faggot"]:
                self.running = False