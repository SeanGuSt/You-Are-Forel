from typing import TYPE_CHECKING
import pygame
from constants import GameState
from objects.map_objects import Monster

if TYPE_CHECKING:
    from ultimalike import GameEngine
    
def combat_inputs(self: 'GameEngine', event):
    current_unit= self.combat_manager.get_current_unit()
    if not current_unit:
        return
    match event.key:
        #Movement/Direction selection
        case pygame.K_UP | pygame.K_DOWN | pygame.K_LEFT | pygame.K_RIGHT:
            if current_unit.virtue_manager.is_overuse_blocking_movement(current_unit):
                self.combat_manager.append_to_combat_log("You can't move!")
                return
            direc = self.get_direction(event.key).value
            tpos = current_unit.add_tuples(current_unit.position, direc)
            messages = []
            if self.attack_mode:
                self.attack_mode = False
                mobjs = self.current_map.get_objects_at(tpos, Monster)
                for obj in mobjs:
                    if obj.hp > 0:
                        self.combat_manager.perform_attack(current_unit, obj)
                        break
                self.combat_manager.conclude_current_player_turn()
            elif self.spell_direction_mode:
                direction = self.get_direction(event.key)
                messages = current_unit.cast_spell(direction = direction)
                self.current_map.revert_map_tiles()
                self.spell_direction_mode = False
            elif self.spell_target_mode:
                if not self.cursor_position:
                    self.cursor_position = current_unit.position
                tx, ty = current_unit.add_tuples(self.cursor_position, self.get_direction(event.key).value)
                if (abs(current_unit.position[0] - tx) + abs(current_unit.position[1] - ty)) < current_unit.prepped_spell.range:
                    self.cursor_position = (tx, ty)
            else:
                if self.current_map.is_passable(tpos):
                    current_unit.old_position = current_unit.position
                    current_unit.position = tpos
                    self.event_manager.timer_manager.start_timer("player_move", 180)
                    self.combat_manager.conclude_current_player_turn()
                    return
                
                warp_node = self.current_map.get_object_by_name("map_edge_teleporter")
                if warp_node and (tpos[0] < 0 or tpos[0] >= self.current_map.width or tpos[1] < 0 or tpos[1] >= self.current_map.height):
                    current_unit.old_position = current_unit.position
                    current_unit.position = tpos
                    self.event_manager.timer_manager.start_timer("player_move", 180)
                    self.combat_manager.conclude_current_player_turn()
                    self.current_map.remove_object(current_unit)
                    if all([party_member not in self.current_map.objects for party_member in self.party.members]):
                        self.handle_teleporter(warp_node)
                        return_node = self.current_map.get_object_by_name("return_node")
                        self.current_map.remove_object(return_node)     
            for message in messages:
                self.combat_manager.append_to_combat_log(message)
            self.handle_map_objects()
        case pygame.K_a:
            if not self.attack_mode:
                self.attack_mode = True
                self.combat_manager.append_to_combat_log(f"{current_unit.name} readies {current_unit.possessive} weapon.")
        case pygame.K_s:
            current_unit.special = True
            self.combat_manager.append_to_combat_log(f"{current_unit.name} prepares to use a special ability.")
        case pygame.K_c:
            self.change_state(GameState.DIALOG)  # Reuse dialog UI for spell input
            self.dialog_manager.awaiting_keyword = True
            self.dialog_manager.waiting_for_input = True
            self.dialog_manager.user_input = ""
            self.spell_input_mode = True
        case pygame.K_SPACE:
            # Wait action
            self.combat_manager.conclude_current_player_turn()
        case pygame.K_RETURN:
            if self.spell_target_mode:
                cursor_position = self.cursor_position
                current_unit.cast_spell(position = cursor_position)
                self.spell_target_mode = False
                self.current_map.revert_map_tiles()
                self.cursor_position = None
            if self.spell_self_mode:
                print("Debug: Arrived at spell self mode")
                current_unit.cast_spell(party_member = current_unit)
                self.spell_self_mode = False
                self.current_map.revert_map_tiles()
                self.cursor_position = None