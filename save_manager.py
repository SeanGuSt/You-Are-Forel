import os
import json
from typing import Tuple, List, TYPE_CHECKING
from objects.characters import Party
from options import GameOptions
from events.events import EventManager
from constants import MAPS_DIR, SAVES_DIR, GameState
import datetime
if TYPE_CHECKING:
    from ultimalike import GameEngine

class SaveManager:
    def __init__(self, engine: 'GameEngine'):
        self.engine = engine
    @staticmethod
    def ensure_directories(foldername: str = ""):
        """Create necessary directories if they don't exist"""
        os.makedirs(SAVES_DIR, exist_ok=True)
        os.makedirs(MAPS_DIR, exist_ok=True)
        if foldername:
            os.makedirs(f"{SAVES_DIR}/{foldername}", exist_ok=True)
    
    def save_game(self, foldername: str):
        """Save game state to file"""
        self.ensure_directories(foldername)
        save_data = {
            "party": self.engine.party.to_dict(),
            "options": self.engine.options.to_dict(),
            "events":self.engine.event_manager.to_dict(),
            "quests": self.engine.quest_log.save_quests(),
            "current_map" : self.engine.current_map.name,
            "time" : list(self.engine.schedule_manager.current_game_time.timetuple()[:6]),
            "old_time" : list(self.engine.schedule_manager.last_game_time.timetuple()[:6]),
            "turn_history": self.engine.schedule_manager.turn_history,
            "version": "0.0"
        }
        
        folderpath = os.path.join(SAVES_DIR, f"{foldername}")
        filepath = os.path.join(folderpath, "player_data.json")
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent = 2)
        for map_name, map in self.engine.maps.items():
            filepath = os.path.join(folderpath, f"objs_{map_name}_updated.json")
            with open(filepath, 'w') as f:
                json.dump(map.to_dict(), f, indent = 2)

    
    def load_game(self, foldername: str) -> Tuple[Party, GameOptions]:
        """Load game state from file"""
        folderpath = os.path.join(SAVES_DIR, foldername)
        
        if not os.path.exists(folderpath):
            raise FileNotFoundError(f"Save folder not found: {folderpath}")
        
        filepath = os.path.join(folderpath, "player_data.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Save file not found: {filepath}")
        with open(filepath, 'r') as f:
            save_data = json.load(f)
        self.engine.party = Party.from_dict(save_data["party"], self.engine)
        self.engine.options = GameOptions.from_dict(save_data.get("options", {}))
        self.engine.event_manager = EventManager.from_dict(save_data["events"], self.engine)
        self.engine.quest_log.load_quests_from_save(save_data["quests"])
        self.engine.schedule_manager.turn_history = save_data.get("turn_history", [])
        self.engine.schedule_manager.current_game_time = datetime.datetime(*save_data["time"])
        self.engine.schedule_manager.last_game_time = datetime.datetime(*save_data["old_time"])
        for file in os.listdir(folderpath):
            if file.startswith("objs_") and file.endswith("_updated.json"):
                filepath = os.path.join(folderpath, file)
                with open(filepath, 'r') as f:
                    updated_object_data = json.load(f)
                map_name = file.split("objs_")[1].split("_updated.json")[0]
                for obj in updated_object_data:
                    if updated_object_data[obj] and updated_object_data[obj]["position"]:
                        updated_object_data[obj]["position"] = (updated_object_data[obj]["position"][0], updated_object_data[obj]["position"][1])
                self.engine.load_map(map_name, updated_object_data)
        self.engine.current_map = self.engine.maps[save_data["current_map"]]
        self.engine.change_state(GameState.TOWN)
        party_leader = self.engine.party.get_leader()
        party_leader.map = self.engine.current_map
        for i in self.engine.party.members:
            self.engine.current_map.add_object(i)
        

    
    @staticmethod
    def get_save_files() -> List[str]:
        """Get list of available save files"""
        SaveManager.ensure_directories()
        
        if not os.path.exists(SAVES_DIR):
            return []
        
        saves = []
        for folder_name in os.listdir(SAVES_DIR):
            if os.path.isdir(os.path.join(SAVES_DIR,folder_name)):
                saves.append(folder_name)
        
        return sorted(saves)
    
