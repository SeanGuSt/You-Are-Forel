from typing import TYPE_CHECKING
import pygame
from constants import GameState, DEFAULT_PLAYER_MOVE_FRAMES, DEFAULT_WAIT_PENALTY
from objects.map_objects import NPC, MapObject
from save_manager import SaveManager

if TYPE_CHECKING:
    from ultimalike import GameEngine
    
    
def travel_inputs(self: 'GameEngine', event) -> dict | None:
    match event.key:
        case pygame.K_SPACE:
            self.event_manager.timer_limits["player_move"] = DEFAULT_PLAYER_MOVE_FRAMES
            self.party.get_leader().old_position = self.party.get_leader().position
            return {"movement_penalty" : DEFAULT_WAIT_PENALTY}
        case pygame.K_UP | pygame.K_DOWN | pygame.K_LEFT | pygame.K_RIGHT:
            direc = self.get_direction(event.key)
            leader = self.party.get_leader()
            pos = leader.position
            tpos = leader.add_tuples(pos, direc.value)
            if self.talk_mode:
                # Handle direction after 'T' press
                self.talk_mode = False
                for obj in self.current_map.get_objects_at(tpos):
                    if obj.__is__(NPC):
                        self.try_talk_to_object(obj)
                    else:
                        self.try_look_at_object(obj)
            elif self.attack_mode:
                self.attack_mode = False
                for obj in self.current_map.get_objects_at(tpos):
                    attacked = self.try_initial_attack(obj, direc.value)
                    if attacked:
                        break
            elif self.look_mode:
                self.look_mode = False
                for obj in self.current_map.get_objects_at(tpos):
                    if obj.__is__(MapObject):
                        if self.try_look_at_object(obj):
                            break
            else:
                moved, movement_penalty = self.party.move(direc.value, self.current_map)
                if moved:
                    return {"movement_penalty" : movement_penalty}
                else:
                    leader.start_bump_animation(direc)
                    for obj in self.current_map.get_objects_at(tpos):
                        if obj.__is__(NPC):
                            if obj.is_hostile:
                                if self.try_initial_attack(obj):
                                    break
                            else:
                                if self.try_talk_to_object(obj):
                                    break
                        elif obj.__is__(MapObject):
                            if self.try_look_at_object(obj):
                                break
                                
        case pygame.K_e:  # Equipment menu
            self.change_state(GameState.MENU_EQUIPMENT)
            self.selected_member = 0
            self.selected_slot = 0
            self.selected_equipment = 0
            self.show_equipment_list = False
        # Menu and command keys
        case pygame.K_d:
            self.talk_mode = True
        case pygame.K_a:
            self.attack_mode = True  # Player must then press direction
        case pygame.K_s:
            self.look_mode = True
        case pygame.K_c:
            self.change_state(GameState.DIALOG)  # Reuse dialog UI for spell input
            self.dialog_manager.awaiting_input = True
            self.dialog_manager.user_input = ""
            self.spell_input_mode = True
        case pygame.K_q:
            self.change_state(GameState.MENU_QUEST_LOG)
            self.current_quest_focus = 0
            self.selected_quest_indices = [0, 0, 0]
        case pygame.K_1 | pygame.K_2 | pygame.K_3 | pygame.K_4 | pygame.K_5 | pygame.K_6 | pygame.K_7 | pygame.K_8 | pygame.K_9:
            member_index = event.key - pygame.K_1
            party_member = self.party.members[member_index]
            caster = self.party.get_leader()
            caster.cast_spell(party_member = party_member)
        case pygame.K_z:
            self.change_state(GameState.MENU_STATS)
        case pygame.K_i:
            self.change_state(GameState.MENU_INVENTORY)
        case pygame.K_o:
            self.change_state(GameState.MENU_OPTIONS)
            self.selected_option = 0
        case pygame.K_F5:  # Quick save
            if self.options.auto_save:
                self.save_manager.save_game("quicksave", self.party, self.options)
                print("Game saved!")
        case pygame.K_F9:  # Quick load
            try:
                self.save_manager.load_game("quicksave")
                print("Game loaded!")
            except FileNotFoundError:
                print("No quicksave found!")
        case pygame.K_F1:  # Save menu
            self.change_state(GameState.MENU_SAVE_LOAD)
            self.is_save_mode = True
            self.selected_save = 0
    return {}