import os
import json
import pygame
from typing import Dict
from constants import *
from sprites.sprites import SpriteDatabase
from combat import CombatManager
from events.cutscenes import CutsceneManager
from dialog.dialog import DialogManager
from events.events import EventManager
from sound.sound import SoundDatabase
from magic.magic import Spell, SpellBook
from schedules.schedule import ScheduleManager
from renderer import Renderer
from objects.characters import Party, Character
from tiles.tiles import Tile
from tiles.tile_database import TileDatabase
from quests.quests import QuestLog
from items.itemz import Item, ItemDatabase
from save_manager import SaveManager
from objects.map_objects import Map, Node, MapObject, MapObjectDatabase, Teleporter, NPC, Monster
from objects.object_templates import Missile

from options import GameOptions

#Inputs
from inputs.main_menu_inputs import main_menu_inputs, options_menu_inputs, save_load_inputs
from inputs.item_menu_inputs import equipment_menu_inputs, stats_menu_inputs, inventory_menu_inputs
from inputs.dialog_ui_inputs import dialog_inputs
from inputs.combat_ui_inputs import combat_inputs
from inputs.travel_ui_inputs import travel_inputs
from inputs.quest_ui_inputs import quest_log_inputs
from inputs.events_inputs import events_inputs
from inputs.debug_inputs import debug_inputs


# Initialize Pygame
pygame.init()
pygame.mixer.init()
pygame.key.set_repeat(DEFAULT_INPUT_REPEAT_DELAY, DEFAULT_INPUT_REPEAT_INTERVAL)
init_map = "Battle Test Map"
init_time = 420#in minutes
init_cutscene = ""

class GameEngine:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.FPS = 60
        self.running = True
        self.antialias_text = True
        # Game state
        self.state = GameState.MAIN_MENU
        self.previous_state = GameState.MAIN_MENU

        self.item_db = ItemDatabase()
        self.map_obj_db = MapObjectDatabase(self)

        self.schedule_manager = ScheduleManager(self)
        self.sound_manager = SoundDatabase()
        self.step_tracker = 1
        
        # Options and save system
        self.options = GameOptions()
        self.selected_option = 0
        self.selected_save = 0
        self.is_save_mode = False

        # Dialog system
        self.dialog_manager = DialogManager(self)
        self.talk_mode = False  # True when waiting for direction after 'T' press
        self.look_mode = False

        self.cutscene_manager = CutsceneManager(self)
        self.save_manager = SaveManager(self)
        self.event_manager = EventManager(self)

        # Equipment menu state
        self.selected_member = 0
        self.selected_slot = 0
        self.selected_equipment = 0
        self.show_equipment_list = False
        self.picking_item_to_show = False
        self.messages = ["", "", "", "", ""]

        self.combat_manager = CombatManager(self)
        self.attack_mode = False

        self.spellbook = SpellBook(self)
        self.spell_input_mode = False
        self.spell_direction_mode = False
        self.spell_target_mode = False
        self.spell_self_mode = False
        self.use_range = -1
        self.cursor_position = None
        self.oops = False
        
        self.sprite_db = SpriteDatabase(self)
        # Initialize game objects (will be set when starting/loading game)
        self.party: Party = Party(self)
        self.maps: Dict[str, Map] = {}
        self.visible_tiles: set[tuple[int, int]] = ()
        self.current_map: Map = None
        self.tile_db = TileDatabase()

        self.quest_log = QuestLog(self)
        self.current_quest_focus = 0
        self.selected_quest_indices = [0, 0, 0]
        
        self.renderer = Renderer(self, self.screen)
        
        # Camera
        self.camera = (0.0, 0.0)
        self.override_camera = False
        self.camera_override = (0.0, 0.0)
        self.prev_screen_x = 0
        self.prev_screen_y = 0
        
    def get_direction(self, key) -> Direction:
        direction = {
            pygame.K_UP: Direction.NORTH,
            pygame.K_DOWN: Direction.SOUTH,
            pygame.K_LEFT: Direction.WEST,
            pygame.K_RIGHT: Direction.EAST,
            pygame.K_SPACE: Direction.WAIT,
        }.get(key)
        if not direction:
            direction = {
                'N': Direction.NORTH,
                'S': Direction.SOUTH,
                'W': Direction.WEST,
                'E': Direction.EAST,
                'X': Direction.WAIT
            }.get(key)
        return direction
    
    def change_state(self, state: GameState):
        self.previous_state = self.state
        self.state = state
        print(f"state is now {self.state}")

    def revert_state(self):
        state_copy = GameState(self.state.value)
        self.state = self.previous_state
        self.previous_state = state_copy
        print(f"state is now {self.state}")
        
    def start_new_game(self):
        """Initialize a new game"""
        self.schedule_manager.advance_time(init_time)

        #Add starting party members
        with open("new_game_party.json", 'r') as f:
            starting_party = json.load(f)
            for name, starting_stats in starting_party.items():
                self.party.add_member(Character.from_dict(name, starting_stats, self))
        
        # Add starting items
        with open("new_game_inventory.json", 'r') as f:
            starting_items = json.load(f)
            for name, quantity in starting_items.items():
                self.party.add_item_by_name(name, quantity)
        
        # Load maps
        self.load_map("overworld")
        self.load_map(init_map)
        
        self.current_map = self.maps[init_map]
        party_leader = self.party.get_leader()
        new_game_spawner = self.current_map.get_object_by_name(NEW_GAME_SPAWNER)
        party_leader.init_position = new_game_spawner.position
        party_leader.position = new_game_spawner.position
        party_leader.map = self.current_map
        for i in self.party.members:
            self.current_map.add_object(i)
        
        if init_cutscene:
            self.cutscene_manager.start_scene(init_cutscene)
            self.state = GameState.CUTSCENE
        else:
            self.state = GameState.TOWN
        self.previous_state = GameState.TOWN
        
    def load_map(self, map_name: str, updated_objs: dict = {}):
        """Load a map from files"""
        try:
            self.maps[map_name] = Map.load_from_files(map_name, self.map_obj_db, self.tile_db, self, updated_objs)
            return True
        except (FileNotFoundError, ValueError) as e:
            print(f"Error loading map {map_name}: {e}")
            # Create empty map as fallback
            return False
    
    def handle_teleporter(self, teleporter: Node, force_work: bool = False):
        """Handle teleporter activation"""
        if not teleporter.activate_by_stepping_on:
            if not force_work:
                return
        target_map = teleporter.args.get("target_map")
        # Load target map if not already loaded
        if target_map not in self.maps:#self.maps is a dictionary of maps
            if not self.load_map(target_map):
                return
        #If the teleport happens mid dialog, be sure the npc being spoken to has a version of itself on the new map.
        talker = self.dialog_manager.current_speaker
        talking_to_someone = talker and self.state == GameState.DIALOG
        # Switch to target map
        for i in self.party.members:
            self.current_map.objects.remove(i)
        self.current_map = self.maps[target_map]
        npc_move_intervals = {}
        for obj in self.current_map.get_objects_at((-99, -99)):
            obj.on_map_load()
        for obj in self.current_map.get_objects_subset(MapObject):
            npc_move_intervals[obj.name] = obj.move_interval
        results = self.schedule_manager.process_map_load(npc_move_intervals)
        self.party.current_map = target_map
        # Set player position based on teleporter type
        if "position" in teleporter.args:
            position = teleporter.args["position"]["from_any"]
            if position:
                node = self.current_map.get_object_by_name(position)
                leader = self.party.get_leader()
                if node and leader:
                    self.current_map.objects.append(leader)
                    leader.old_position = node.position
                    leader.position = node.position
        elif "positions" in teleporter.args:
            # Multiple positions for party members (combat maps only, for now.)
            positions = teleporter.args["positions"]["from_any"]
            if positions:
                for i in range(len(self.party.members)):
                    node = self.current_map.get_object_by_name(positions + str(i))
                    self.current_map.objects.append(self.party.members[i])
                    if node:
                        self.party.members[i].position = node.position
        # Update game state based on target map
        if talking_to_someone:
            new_talker = self.current_map.get_object_by_name(talker.name)
            if new_talker:
                self.dialog_manager.current_speaker = new_talker
                return
            else:
                raise Exception(f"A MapObject with the same name as {talker.name} should be present when warping to {self.current_map.name} during dialog.")
        elif "combat" in target_map:
            self.combat_manager.enter_combat_mode(teleporter.args.get("allies_in_combat", []))
        else:
            if self.state == GameState.COMBAT:
                self.combat_manager.exit_combat_mode()
            self.change_state(GameState.TOWN)
    
    def handle_map_objects(self):
        """Check for and handle map objects at player position"""
        objects_at_position = self.current_map.get_objects_at(self.party.get_leader().position)
        for obj in objects_at_position:
            if obj.__is__(Teleporter):
                self.handle_teleporter(obj)
                break
            event_start = obj.args.get("event_start", "")
            
            if event_start:
                remove_object = self.event_manager.start_event(event_start, obj)
                if remove_object:
                    self.current_map.remove_object(obj)
    
    def get_combat_map_name(self, attacker_tile_name: str, target_tile_name: str, target_tile: Tile) -> str:

        """Generate combat map name based on tile types"""
        if attacker_tile_name == target_tile_name:
            # Same tile type - use the tile's combat map
            return f"combat_{target_tile_name}"
        else:
            # Different tile types - use hybrid map
            # Sort tile names for consistent naming
            tiles = sorted([attacker_tile_name, target_tile_name])
            return f"combat_{tiles[0]}_{tiles[1]}"

    def update_world_after_action(self, movement_penalty):
        self.schedule_manager.advance_time(movement_penalty)
        leader = self.party.get_leader()
        self.handle_map_objects()
        # Check for triggered actions for all objects
        for obj in self.current_map.get_objects_subset():
            actions = self.schedule_manager.get_current_event(obj.name)
            if actions:
                obj.update_from_schedule()
                
            obj.move_one_step()

    #@time_function("Updating camera")
    def get_movement_timer_name(self, entity):
        """Get the correct timer name for an entity's movement"""
        timer_manager = self.event_manager.timer_manager
        
        # Check in priority order (same as your renderer logic)
        obj_in_walkers = entity in self.event_manager.walkers
        
        # 1. Knockback has highest priority
        if obj_in_walkers and timer_manager.is_active(f"{entity.name}_knockback"):
            return f"{entity.name}_knockback"
        
        # 2. Player movement
        elif timer_manager.is_active("player_move"):
            return "player_move"
        
        # 3. Player bump (only for leader)
        elif entity == self.party.get_leader() and timer_manager.is_active("player_bump"):
            return "player_bump"
        
        # 4. Event movement for walkers
        elif obj_in_walkers and timer_manager.is_active(f"event_wait_{entity.name}"):
            return f"event_wait_{entity.name}"
        
        # 5. Combat/enemy movement
        elif entity in self.combat_manager.walkers and timer_manager.is_active("enemy_move"):
            return "enemy_move"
        
        # 6. Fallback - no active movement
        else:
            return None
    
    def get_interpolated_position(self, entity):
        """Get the interpolated position for an entity, handling all timing logic centrally"""
        timer_name = self.get_movement_timer_name(entity)
        
        # If no active movement timer, return current position
        if timer_name is None:
            return entity.position
        
        # Special handling for bump movement (doesn't use interpolation the same way)
        if timer_name == "player_bump":
            return entity.position  # Let bump_movement handle this separately
            
        progress = self.event_manager.timer_manager.get_progress(timer_name, False)
        
        if progress >= 1.0:
            return entity.position
            
        # Calculate delta and interpolate
        delta = entity.subtract_tuples(entity.position, entity.old_position)
        return entity.add_tuples(entity.old_position, entity.multiply_tuples(delta, progress))
    
    def update_camera(self):
        leader = self.party.get_leader()
        if not leader:
            if self.state in [GameState.MAIN_MENU]:
                return
            else:
                raise ValueError
        
        # Get interpolated position using centralized method
        current_pos = self.get_interpolated_position(leader)
        
        # Center camera on leader (with sub-tile precision)
        # Use integer division to avoid floating point precision issues
        camera_x = current_pos[0] - MAP_WIDTH // 2
        camera_y = current_pos[1] - MAP_HEIGHT // 2
        
        # Handle odd MAP dimensions to maintain consistent centering
        if MAP_WIDTH % 2 == 1:
            camera_x -= 0.5
        if MAP_HEIGHT % 2 == 1:
            camera_y -= 0.5
        
        # Clamp to map bounds (allowing partial tile views)
        max_cam_x = self.current_map.width - MAP_WIDTH
        max_cam_y = self.current_map.height - MAP_HEIGHT
        
        self.camera = (
            max(0.0, min(float(max_cam_x), camera_x)),
            max(0.0, min(float(max_cam_y), camera_y)),
        )
        
    def try_talk_to_object(self, obj: NPC):
        if self.state == GameState.COMBAT:
            return False
        if self.dialog_manager.start_dialog(obj):
            self.change_state(GameState.DIALOG)
            self.party.get_leader().state = ObjectState.TALK
            return True
        
        return False  # No talkable object found
    
    def try_look_at_object(self, obj: MapObject):
        if self.state == GameState.COMBAT:
            return False
        # Find talkable objects at target position
        if self.dialog_manager.start_looking(obj):
            self.change_state(GameState.DIALOG)
            return True
        
        return False  # No searchable object found
    
    def try_initial_attack(self, obj: MapObject, direc):
        if not obj.__is__(MapObject):
            return False
        if obj.can_be_attacked:
            self.change_state(GameState.COMBAT)
            attacker = self.party.get_leader()
            
            # Get tiles for both attacker and target
            obj_tile = self.current_map.get_tile_lower(obj.x, obj.y)
            attacker_tile = self.current_map.get_tile_lower(attacker.x, attacker.y)
            
            
            # Determine combat map name
            combat_map_name = self.get_combat_map_name(attacker_tile.name, obj_tile.name, direc)
            
            # Create a temporary teleporter object to handle the transition
            obj.args = obj.args | {
                    'target_map': combat_map_name,
                    "positions" : {
                        "from_any": f"{obj_tile.name}_node_"
                    }
                }
            mo = self.map_obj_db.create_obj("return_node", "node", {"x" : obj.x, "y" : obj.y, "args" : {}})
            self.current_map.add_object(mo)
            # Setup enemy positions based on attack direction
            old_map = self.current_map.name
            # Handle the teleportation to combat map
            self.handle_teleporter(obj)
            edge_teleporter = self.map_obj_db.create_obj("edge_teleporter", "node", {"x" : -99, "y" : -98, "args" : {}})
            self.current_map.create_ring_of_return_teleporters(old_map)
            return True
        return False
    
    #@time_function("Handle Input: ")
    def handle_input(self):
        input_results_for_updates = {}
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                match self.state:
                    case GameState.MAIN_MENU:
                        main_menu_inputs(self, event)
                    case GameState.MENU_OPTIONS:
                        options_menu_inputs(self, event)
                    case GameState.MENU_SAVE_LOAD:
                        save_load_inputs(self, event)
                    case GameState.MENU_EQUIPMENT:
                        equipment_menu_inputs(self, event)
                    case GameState.MENU_STATS:
                        stats_menu_inputs(self, event)
                    case GameState.MENU_INVENTORY:
                        inventory_menu_inputs(self, event)
                    case GameState.MENU_QUEST_LOG:
                        quest_log_inputs(self, event)
                    case GameState.DEBUG:
                        debug_inputs(self, event)
                    case GameState.DIALOG:
                        if "teleporter" in self.event_manager.delayed_events or not self.dialog_manager.waiting_for_input:
                            continue
                        dialog_inputs(self, event)
                    case GameState.EVENT:
                        if not self.event_manager.waiting_for_input:
                            continue
                        events_inputs(self, event)
                    case GameState.CUTSCENE:
                        match event.key:
                            case pygame.K_RETURN:
                                self.cutscene_manager.end_scene()
                                self.revert_state()
                                print(self.state)
                            case pygame.K_SPACE:
                                if not self.cutscene_manager.advance_scene():
                                    self.cutscene_manager.end_scene()
                                    self.revert_state()
                    case GameState.COMBAT:
                        if self.event_manager.walkers or not self.combat_manager.player_turn or self.combat_manager.attack_frame or self.combat_manager.player_made_move:
                            continue
                        combat_inputs(self, event)
                    case GameState.TOWN:
                        if self.event_manager.timer_manager.is_active("player_move") or self.event_manager.timer_manager.is_active("player_bump"):
                            continue
                        input_results_for_updates = travel_inputs(self, event)
        return input_results_for_updates
    
    def adjust_option(self, direction):
        """Adjust the selected option value"""
        if self.selected_option == 0:  # Music Volume
            self.options.music_volume = max(0.0, min(1.0, self.options.music_volume + direction * 0.1))
        elif self.selected_option == 1:  # Sound Volume
            self.options.sound_volume = max(0.0, min(1.0, self.options.sound_volume + direction * 0.1))
        elif self.selected_option == 2:  # Fullscreen
            if direction != 0:
                self.options.fullscreen = not self.options.fullscreen
                # Note: Actually implementing fullscreen would require display mode changes
        elif self.selected_option == 3:  # Show Grid
            if direction != 0:
                self.options.show_grid = not self.options.show_grid
        elif self.selected_option == 4:  # Auto Save
            if direction != 0:
                self.options.auto_save = not self.options.auto_save
    
    def save_options(self):
        """Save options to file"""
        try:
            SaveManager.ensure_directories()
            with open(os.path.join(SAVES_DIR, "options.json"), 'w') as f:
                json.dump(self.options.to_dict(), f, indent=2)
            print("Options saved!")
        except Exception as e:
            print(f"Error saving options: {e}")
    
    def load_options(self):
        """Load options from file"""
        try:
            options_file = os.path.join(SAVES_DIR, "options.json")
            if os.path.exists(options_file):
                with open(options_file, 'r') as f:
                    options_data = json.load(f)
                self.options = GameOptions.from_dict(options_data)
        except Exception as e:
            print(f"Error loading options: {e}")

    def append_to_message_log(self, text):
        self.messages.pop(0)
        self.messages.append(text)
    
    def handle_save_load_selection(self):
        """Handle save/load menu selection"""
        save_files = SaveManager.get_save_files()
        
        if self.is_save_mode:
            if self.selected_save == 0:
                # New save - prompt for filename (simplified: use timestamp)
                import time
                filename = f"save_{int(time.time())}"
                self.save_manager.save_game(filename)
                print(f"Game saved as {filename}!")
                self.revert_state()
            elif self.selected_save - 1 < len(save_files):
                # Overwrite existing save
                filename = save_files[self.selected_save - 1]
                self.save_manager.save_game(filename)
                print(f"Game saved as {filename}!")
                self.revert_state()
        else:
            # Load mode
            if self.selected_save < len(save_files):
                filename = save_files[self.selected_save]
                try:
                    self.save_manager.load_game(filename)
                    print(f"Game loaded from {filename}!")
                except Exception as e:
                    print(f"Error loading save: {e}")

    def update(self, update_dict: dict = {}):
        movement_penalty = update_dict.get("movement_penalty", 0)#If no time passes, the world shouldn't change.
        if movement_penalty:
            self.update_world_after_action(movement_penalty)


    #@time_function("Render Frame: ")  
    def render(self):
        match self.state:
            case GameState.MAIN_MENU:
                self.renderer.render_main_menu()
            case GameState.MENU_STATS:
                self.renderer.render_stats_menu()
            case GameState.MENU_INVENTORY:
                print("HELLO")
                self.renderer.render_inventory_menu()
            case GameState.MENU_OPTIONS:
                self.renderer.render_options_menu()
            case GameState.MENU_SAVE_LOAD:
                save_files = SaveManager.get_save_files()
                self.renderer.render_save_load_menu(save_files)
            case GameState.MENU_EQUIPMENT:
                self.renderer.render_equipment_menu()
            case GameState.MENU_QUEST_LOG:
                self.renderer.render_quest_log()
            case GameState.DIALOG:
                # Render game world in background
                self.screen.fill(BLACK)
                if self.current_map and self.party:
                    self.renderer.render_map()
                    
                    self.renderer.render_sidebar_stats()
                # Render dialog on top
                self.renderer.render_dialog()

            case GameState.CUTSCENE:
                self.screen.fill(BLACK)
                self.renderer.render_cutscene()
            case GameState.DEBUG:
                # Render game world in background
                self.screen.fill(BLACK)
                if self.current_map and self.party:
                    self.renderer.render_map()
                    
                    self.renderer.render_sidebar_stats()
                self.renderer.render_debug()
            case GameState.EVENT:
                # Render game world in background
                self.screen.fill(BLACK)
                if self.current_map and self.party:
                    self.renderer.render_map()
                    
                    self.renderer.render_sidebar_stats()
                self.renderer.render_event_dialog()
            case _:
                # Render game world
                self.screen.fill(BLACK)
                if self.current_map and self.party:
                    self.renderer.render_map()
                    self.renderer.render_sidebar_stats()
                    if self.state == GameState.COMBAT:
                        self.renderer.render_combat_log()
                    else:
                        self.renderer.render_bottom_text_box()
                    if self.spell_target_mode and self.cursor_position:
                        x, y = self.cursor_position
                        rect = pygame.Rect((x - self.camera[0])*TILE_WIDTH + TILE_WIDTH//2, (y - self.camera[1])*TILE_HEIGHT + TILE_HEIGHT//2, 8, 8)
                        pygame.draw.ellipse(self.screen, GRAY, rect)
        fps = self.clock.get_fps()
        fps_text = self.renderer.font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
        self.renderer.screen.blit(fps_text, (10, 10))
        pygame.display.flip()
    
    #@time_function("This frame")
    def while_running(self):
        if self.current_map:
            self.update_camera()
            if not self.event_manager.timer_manager.is_active("player_move"):
                for obj in self.current_map.get_objects_subset(Missile):
                    if obj.destroy_after_use:
                        obj.destroy()
                    
                start_event = self.event_manager.delayed_events.get("event_start", "")
                if start_event:
                    self.event_manager.delayed_events.pop("event_start")
                    self.event_manager.start_event(start_event, self.event_manager.event_master, True)
            if self.event_manager.delayed_events:
                if "event_start" in self.event_manager.delayed_events and self.dialog_manager.awaiting_keyword:
                    event = self.event_manager.delayed_events.pop("event_start")
                    self.event_manager.start_event(event, self.event_manager.event_master, True)
                elif "teleporter" in self.event_manager.delayed_events:
                    if self.event_manager.timer_manager.get_progress("teleporter_delay") >= 1.0:
                        self.handle_teleporter(self.event_manager.delayed_events["teleporter"], True)
                        self.event_manager.delayed_events = {}
                        self.dialog_manager.current_line_index += 1
                        self.dialog_manager.current_line = self.dialog_manager.get_current_line()
        input_results_for_updates = self.handle_input()
        self.update(input_results_for_updates)
        any_active = self.event_manager.timer_manager.any_active()
        if self.dialog_manager.current_lines:
            self.dialog_manager.advance_dialog()
        if self.event_manager.current_event_queue:
            self.event_manager.advance_queue()
        if self.event_manager.walkers:
            self.event_manager.continue_walk()
        if self.state == GameState.COMBAT and not any_active:
            self.combat_manager.advance_turn()
            if self.combat_manager.player_turn:
                self.combat_manager.update_special()
        self.render()
        self.clock.tick(self.FPS)  # Cap to 60 FPS
        
    def run(self):
        # Load options on startup
        self.load_options()
        
        while self.running:
            self.while_running()
            
        pygame.quit()

# Main execution
if __name__ == "__main__":
    # Start memory monitor in background
    #threading.Thread(target=monitor_memory, daemon=True).start()
    #threading.Thread(target = time_function, daemon = True)
    
    game = GameEngine()
    game.run()