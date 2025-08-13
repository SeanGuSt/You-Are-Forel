from constants import MAP_HEIGHT, MAP_WIDTH, MAPS_DIR, GameState, ObjectState, DIRECTIONS
from objects.object_templates import Monster, CombatStatsMixin
from typing import TYPE_CHECKING
import os, json
import pygame
if TYPE_CHECKING:
    from objects.characters import Character
    from ultimalike import GameEngine


# Combat management class
class CombatManager:
    def __init__(self, game_engine: 'GameEngine'):
        self.engine = game_engine
        self.active_combat = False
        self.current_unit_index = 0
        self.attack_frame: int = 0
        self.player_turn = True
        self.selected_spell = None
        self.spell_input_mode = False
        self.targeting_mode = None  # "direction" or "target"
        self.cursor_position = None
        self.enemy_turn_queue = []
        self.combat_log = ["" for _ in range(5)]
        self.combat_scroll_index = 0
        self.current_enemy_index = 0
        self.walkers = []
        self.enemy_turn_in_progress = False
        self.enemy_move_duration = self.engine.FPS//6  # frames for enemy move animation

    def enter_combat_mode(self, allies_in_combat: list = []):
        self.active_combat = True
        self.current_unit_index = 0
        self.player_turn = True
        self.engine.change_state(GameState.COMBAT)
        can_spawn_monsters = len(allies_in_combat) > 0
        monster_node_index = -1
        while can_spawn_monsters:
            monster_node_index += 1
            node = self.engine.current_map.get_object_by_name("monster_node" + str(monster_node_index))
            if node:
                name = allies_in_combat[monster_node_index]
                monster_dict = {"object_type": "monster", "x" : node.position[0], "y" : node.position[1], "args" : {}}
                monster = self.engine.map_obj_db.create_obj(name, "monster", monster_dict)
                monster.map = self.engine.current_map
                self.engine.current_map.add_object(monster)
            else:
                can_spawn_monsters = False

    def exit_combat_mode(self):
        self.active_combat = False
        self.selected_spell = None
        self.spell_input_mode = False
        self.cursor_position = None
        self.combat_log = ["", "", "", "", ""]
        self.combat_scroll_index = 0
        self.engine.revert_state()

    def is_in_combat(self):
        return self.active_combat

    def get_hostile_objects_in_view(self):
        objects = self.engine.current_map.get_objects_subset(Monster)
        camera_x, camera_y = self.engine.camera
        return [
            obj for obj in objects if obj.is_hostile
            and camera_x <= obj.position[0] < camera_x + MAP_WIDTH
            and camera_y <= obj.position[1] < camera_y + MAP_HEIGHT
        ]
            

    def perform_attack(self, attacker: CombatStatsMixin, target: CombatStatsMixin):
        damage = max(1, attacker.get_total_power() - target.get_total_guard())
        target.hp -= damage
        target.is_hostile = True
        self.append_to_combat_log(f"{attacker.name} hits {target.name} for {damage} damage!")
        if target.hp <= 0:
            self.engine.current_map.remove_object(target)
            self.append_to_combat_log(f"{target.name} was defeated!")
        
        return []
    
    def append_to_combat_log(self, text):
        if not self.combat_log[0]:
            self.combat_log.pop(0)
        else:
            self.combat_scroll_index = len(self.combat_log) - 5
        self.combat_log.append(text)


    
    def get_current_unit(self):
        if self.current_unit_index < len(self.engine.party.members):
            unit = self.engine.party.members[self.current_unit_index]
            return unit
        return None

    def advance_turn(self):
        messages = self.engine.party.members[self.current_unit_index].virtue_manager.apply_turn_end_penalties(self.engine.party.members[self.current_unit_index])
        for message in messages:
            self.append_to_combat_log(message)
        self.current_unit_index += 1

        if self.current_unit_index >= len(self.engine.party.members):
            self.current_unit_index = 0
            self.player_turn = False
            self.start_enemy_turns()

    def start_enemy_turns(self):
        """Initialize the enemy turn sequence"""
        self.enemy_turn_queue = self.get_hostile_objects_in_view()
        self.current_enemy_index = 0
        self.enemy_turn_in_progress = False
        
        if self.enemy_turn_queue:
            self.execute_next_enemy_turn()
        else:
            # No enemies, return to player turn
            self.player_turn = True

    def execute_next_enemy_turn(self):
        """Execute the current enemy's turn"""
        print(f"Player turn is set to {self.player_turn}")
        if self.current_enemy_index < len(self.enemy_turn_queue):
            current_enemy = self.enemy_turn_queue[self.current_enemy_index]
            if current_enemy.__is__(Monster):
                # Store old position before move
                current_enemy.old_position = current_enemy.position
                
                # Execute the enemy's battle tactics
                current_enemy.my_battle_tactics()
                
                # Start the movement animation timer
                self.enemy_turn_in_progress = True
                self.engine.event_manager.timer_manager.start_timer("enemy_move",150)
                # Add to walkers list for animation (similar to player movement)
                self.walkers.append(current_enemy)
        else:
            # All enemies have moved, return to player turn
            self.finish_enemy_turns()
    def update_special(self):
        player = self.get_current_unit()
        if not player:
            return
        if not player.special:
            return
        self.attack_frame += 1
        if self.attack_frame % 3 == 1:
            attack_direction = DIRECTIONS[self.attack_frame // 3]#hit a square in the ith direction
            print(self.attack_frame, attack_direction)
            for obj in self.engine.current_map.get_objects_at(player.add_tuples(player.position, attack_direction.value), CombatStatsMixin):
                if obj.can_be_pushed and not obj.flying:
                    self.append_to_combat_log(f"{player.name} sent {obj.name} flying back 2 spaces!")
                    obj.push(attack_direction, 2)#apply knockback, if possible (object is added to event_manager.walkers here)
                    break
        if self.attack_frame > 21:# We've hit all eight adjacent squares
            if not self.engine.event_manager.walkers:#Don't proceed to the next turn until all animations are finished
                self.attack_frame = 0
                player.special = False
                self.advance_turn()
            else:
                self.attack_frame = 21
        

    def end_push(self):
        for obj in self.engine.event_manager.walkers:
            if obj.state == ObjectState.KNOCKBACK:
                if not self.engine.event_manager.timer_manager.is_active(f"{obj.name}_knockback"):
                    obj.state = ObjectState.STAND
                    self.engine.event_manager.walkers.remove(obj)
    def update_enemy_turn(self):
        """Call this in your main game loop to handle enemy turn progression"""
        if not self.player_turn and self.enemy_turn_in_progress:
            # Check if current enemy's move animation is complete
            timer_manager = self.engine.event_manager.timer_manager
            current_enemy = self.enemy_turn_queue[self.current_enemy_index]
            if not (timer_manager.is_active("enemy_move") or timer_manager.is_active(f"{current_enemy.name}_knockback")):
                self.finish_current_enemy_turn()

    def finish_current_enemy_turn(self):
        """Clean up current enemy turn and move to next"""
        current_enemy = self.enemy_turn_queue[self.current_enemy_index]
        
        # Update old position
        current_enemy.old_position = current_enemy.position
        
        # Move to next enemy
        self.current_enemy_index += 1
        self.enemy_turn_in_progress = False
        self.walkers.remove(current_enemy)
        
        # Small delay before next enemy (optional)
        # You could add a brief pause here if desired
        
        self.execute_next_enemy_turn()

    def finish_enemy_turns(self):
        """Clean up after all enemy turns are complete"""
        self.enemy_turn_queue = []
        self.current_enemy_index = 0
        self.enemy_turn_in_progress = False
        
        # Clear any remaining timers
        self.engine.event_manager.timer_manager.cancel_timer("enemy_move")
        
        self.player_turn = True