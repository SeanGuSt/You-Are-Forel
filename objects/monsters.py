import os
from dataclasses import dataclass, asdict, fields, MISSING
import random
import json, pygame
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from tiles.tiles import Tile
from tiles.tile_database import TileDatabase
from constants import *
import copy
from objects.object_templates import Monster, CombatStatsMixin, Spawner, register_node_type
@register_node_type("monsterkesveltalleythief")
class MonsterKesveltAlleyThief(Monster):
    power = 3
    can_move_diagonally = True
    def my_battle_tactics(self):
        if self.hp <= 0:
            return
        if not self.current_target:
            #A thief will prioritize whoever is closest.
            self.current_target = self.get_closest_obj(self.engine.party.members)
        #Here, it's more like "can attack diagonally"
        dist, dist_tup = self.distance(self.current_target, self.can_move_diagonally)
        if dist <= 1:
            damage = self.attack(self.current_target)
            #Only steal gold from the player if you attacked one of their units.
            if damage and self.current_target in self.engine.party.members:
                if self.engine.party.gold > damage:
                    self.engine.party.gold -= damage
                    self.engine.combat_manager.append_to_combat_log(f"{self.name} also managed to steal {damage} gold!")
                else:
                    self.engine.party.gold = 0
                    self.engine.combat_manager.append_to_combat_log(f"{self.name} also managed to steal the rest of the party's gold!")
            return
        direc = self.get_sign(dist_tup)
        #If the target is in a strictly cardinal direction
        if any([d == 0 for d in direc]):
            print("I am too far, but my target is in sight.")
            new_pos = self.add_tuples(self.position, direc)
            objects_at_new_pos = self.map.get_objects_at(new_pos, subtype=Monster)
            if not objects_at_new_pos:
                self.old_position = self.position
                self.position = new_pos
                self.last_move_direction = Direction(direc)
                return
            for obj in objects_at_new_pos:
                if not obj.is_passable and not self.is_honorable:
                    print("I made it to here")
                    damage = self.attack(obj)
                    self.engine.combat_manager.append_to_combat_log(f"{self.name} attacked {obj.name} because {obj.pronoun} was between {self.prepositional} and {self.current_target.name}")
                    if obj.hp <= 0:
                        self.old_position = self.position
                        self.position = new_pos
                        self.last_move_direction = Direction(direc)
                    return
            self.old_position = self.position
            self.position = new_pos
            self.last_move_direction = Direction(direc)
            return
        else:
            direc_choices = [(direc[0], 0), (0, direc[1])]
            direc_choice = random.choice(direc_choices)
            new_pos = self.add_tuples(self.position, direc_choice)
            objects_at_new_pos = self.map.get_objects_at(new_pos, subtype=Monster)
            if not objects_at_new_pos:
                self.old_position = self.position
                self.position = new_pos
                self.last_move_direction = Direction(direc_choice)
                return
            direc_choices.remove(direc_choice)
            direc_choice = direc_choices[0]
            new_pos = self.add_tuples(self.position, direc_choice)
            objects_at_new_pos = self.map.get_objects_at(new_pos, subtype=Monster)
            if not objects_at_new_pos:
                self.old_position = self.position
                self.position = new_pos
                self.last_move_direction = Direction(direc_choice)
                return
            for obj in objects_at_new_pos:
                if not obj.is_passable and not self.is_honorable:
                    damage = self.attack(obj)
                    self.engine.combat_manager.append_to_combat_log(f"{self.name} attacked {obj.name} because {obj.pronoun} was between {self.prepositional} and {self.current_target.name}")
                    if obj.hp <= 0:
                        self.old_position = self.position
                        self.position = new_pos
                        self.last_move_direction = Direction(direc_choice)
                else:
                    self.old_position = self.position
                    self.position = new_pos
                    self.last_move_direction = Direction(direc_choice)
                return
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Generic People", 0, 7]}               


@register_node_type("monsterguardrookie")
class MonsterGuardRookie(Monster):
    power = 2
    max_hp = 20
    def my_battle_tactics(self):
        if self.engine.combat_manager.round_counter == self.args["pause_round"]:
            self.args["pause_round"] = -1
            return
        if not self.current_target:
            self.current_target = self.engine.party.get_leader()
        
        dist = self.subtract_tuples(self.current_target.position, self.position)
        dx, dy = self.get_sign(dist)
        
        # 1. Attack if adjacent (orthogonally adjacent only)
        if dist in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            self.attack(self.current_target)
        
        # 2. If not in same column, move toward target's column
        elif dist[0]:  # Not in same column
            new_pos = self.add_tuples(self.position, (dx, 0))
            if self.map.is_passable(new_pos):
                self.old_position = self.position
                self.position = new_pos
                self.last_move_direction = Direction((dx, 0))
        
        # 3. If in same column, move toward target's row
        elif not dist[0]:  # In same column
            new_pos = self.add_tuples(self.position, (0, dy))
            if self.map.is_passable(new_pos):
                self.old_position = self.position
                self.position = new_pos
                self.last_move_direction = Direction((0, dy))
        
        # 4. If we reach here, we couldn't move - skip turn
        # (No action needed, turn ends naturally)
    
    def attacked(self, attacker, damage):
        self.current_target = attacker
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Generic People", 0, 3], "pause_round" : -1}
    @classmethod
    def from_dict(cls, data, engine):
        cls = super().from_dict(data, engine)
        return cls

@register_node_type("monstereventtrigger")
class MonsterEventTrigger(Monster):
    @classmethod
    def from_dict(cls, data, engine):
        cls = super().from_dict(data, engine)
        return cls

    def my_battle_tactics(self):
        print(f"round counter is now {self.engine.combat_manager.round_counter} out of {self.args.get("round_timer", 9999)}")
        if self.engine.combat_manager.round_counter >= self.args.get("round_timer", 9999):
            print("PARTY'S OVER")

            self.engine.combat_manager.exit_combat_mode(False)
            self.engine.change_state(GameState.EVENT)
            return
        

@register_node_type("slime")
class Slime(Spawner, Monster):
    absorption_factor = 1
    same_tile_damage_scale = 0.2
    attached_to = None
    @staticmethod
    def default_args():
        return {"spritesheet" : ["Slime", 0, 0]}
    def my_battle_tactics(self):
        if self.hp <= 0:
            return
        super().my_battle_tactics()
        if not self.current_target:
            self.current_target = self.get_closest_obj()
        #If target is adjacent (or since this is a slime, on the same tile) do attack
        if self.distance(self.current_target)[0] <= 1:
            self.attack(self.current_target)
        #If not, but a fellow slime is nearby, absorb it to regain health.
        elif self.hp < self.get_max_hp():
            for obj in self.get_objects_in_adjacent_tiles():
                if not self.absorb_nearby_fellows(obj):
                    break
        #Finally, if two slimes are present in the same tile (this SHOULD only be possible when they're attached to the same host), 
        #the second slime (the one executing this function) should always absorb the first, even if they're at full health
        for obj in self.map.get_objects_at(self.position, Slime):
            if not self.absorb_nearby_fellows(obj):
                break
    def update(self):
        super().update()
        timer_manager = self.engine.event_manager.timer_manager
        match self.state:
            case ObjectState.STAND:#Idle animation
                num_frames = 1
                frame = (pygame.time.get_ticks() // 200) % num_frames
                self.engine.sprite_db.get_sprite(self, new_col = frame)
                pass
            case ObjectState.WALK:
                pass
            case ObjectState.DYING:
                if self.engine.event_manager.timer_manager.get_progress(f"{self.name}_dying") >= 1.0:
                    self.state = ObjectState.DEATH
            case ObjectState.DEATH:
                pass
            case ObjectState.ATTACKED:
                self.state = self.after_state
            case ObjectState.ATTACHING:
                num_frames = 3
                frame = int(num_frames*timer_manager.get_progress(f"enemy_move"))
                if frame >= num_frames:
                    self.engine.sprite_db.get_sprite(self, 0, 0)
                    self.state = self.after_state
                    self.state = ObjectState.ATTACHED
                    self.after_state = ObjectState.ATTACHED
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = 2 + frame)
                    
            case ObjectState.ATTACHED:
                if self.attached_to and False:
                    self.old_position = self.attached_to.old_position
                    self.position = self.attached_to.position
            case ObjectState.ATTACK_MELEE:
                num_frames = 3
                frame = int(num_frames*timer_manager.get_progress(f"enemy_move"))
                if frame >= num_frames:
                    self.engine.sprite_db.get_sprite(self, 0, 0)
                    self.state = self.after_state
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = 2 + frame)
            case ObjectState.SLIME_SPLIT:
                num_frames = 8
                frame = int(num_frames*timer_manager.get_progress(f"{self.name}_split"))
                if frame >= num_frames:
                    self.engine.sprite_db.get_sprite(self, 0, 0)
                    self.state = self.after_state
                else:
                    self.engine.sprite_db.get_sprite(self, new_col = frame)
        
    def attack(self, target: CombatStatsMixin):
        if not target:
            return
        if target.body_status_ex == ExternalBodyStatus.ON_FIRE and not self.attached_to:
            self.hp = -999
            self.engine.sprite_db.get_sprite(self, 0, 3)
            self.attacked(self)
            self.engine.combat_manager.append_to_combat_log(f"{self.name} tried to attach itself to {target.name}, but ended up being roasted alive instead!")
            return
        damage = 0
        if self.attached_to:
            damage = int(self.same_tile_damage_scale*self.attached_to.get_max_hp())
        damage = super().attack(target, damage)
        if not target.parasite_ex or target.parasite_ex.object_type == "slime":
            self.attached_to = target
            self.current_target = target
            self.old_position = self.position
            self.position = target.position
            target.parasite_ex = self
            self.state = ObjectState.ATTACHING
            target.body_status_ex = ExternalBodyStatus.PARASITE
            
    def attacked(self, attacker: CombatStatsMixin, damage: int = 0):
        super().attacked(attacker, damage)
        if self.hp <=0:
            self.is_passable = True
            if self.attached_to:
                self.attached_to.parasite_ex = None
                if self.attached_to.body_status_ex == ExternalBodyStatus.PARASITE:
                    self.attached_to.body_status_ex = None
                elif self.attached_to.body_status_ex == ExternalBodyStatus.ON_FIRE:
                    self.engine.sprite_db.get_sprite(self, new_col = 7)
                self.attached_to = None
            else:
                self.engine.sprite_db.get_sprite(self, new_col = 1)
            self.color = RED
            self.engine.event_manager.timer_manager.start_timer(f"{self.name}_dying", 500)
            self.engine.combat_manager.append_to_combat_log(f"{self.name} died")
            self.state = ObjectState.DYING
            return
        self.state = ObjectState.ATTACKED
        half_hp = self.hp // 2
        if half_hp <= 0:
            return
        new_slime = self.spawn_object_at_position("slime", "", self.add_tuples(self.position, (1, 0)))
        self.hp = half_hp
        self.args["spritesheet"][1] = 1
        self.state = ObjectState.SLIME_SPLIT
        new_slime.hp = half_hp
        new_slime.current_target = attacker
        new_slime.args["spritesheet"][1] = 2
        new_slime.state = ObjectState.SLIME_SPLIT
        self.engine.event_manager.timer_manager.start_timer(f"{self.name}_split", 400)
        self.engine.event_manager.timer_manager.start_timer(f"{new_slime.name}_split", 400)
                
    def absorb_nearby_fellows(self, obj: CombatStatsMixin):
        """
        The function that decides if a fellow adjacent slime will be absorbed in order to restore itself. 
        Won't try to continue doing this if health is filled up
        """
        #Absorbing yourself doesn't make much sense now does it?
        if obj.name == self.name:
            return True
        if obj.__is__(Slime) and obj.hp > 0:
            amount_restored = self.restore_hp(self.absorption_factor*obj.hp // 2)
            self.engine.combat_manager.append_to_combat_log(f"{self.name} absorbed {obj.name}, regaining {amount_restored} health!")
            obj.hp = -1
            obj.is_passable = True
            obj.attached_to = None
        if self.hp >= self.get_max_hp():
            return False
        return True

@register_node_type("templerenald")
class TempleRenald(Monster):
        def my_battle_tactics(self):
            super().my_battle_tactics()
            if not self.current_target:
                self.current_target = self.engine.party.get_leader()
            match self.state:
                case ObjectState.STAND:
                    if self.hp == self.max_hp:
                        pass
