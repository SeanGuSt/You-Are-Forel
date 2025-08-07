import os, json
from constants import GameState, EVENT_DIR
class CutsceneManager:
    def __init__(self, engine):
        self.cutscenes: dict = {}
        self.cutscene: list = []
        self.engine = engine
        self.load_scenes()
        self.current_line_index: int = 0
    def start_scene(self, cutscene_id: str):
        if cutscene_id not in self.cutscenes:
            return False
        self.cutscene = self.cutscenes[cutscene_id]
        self.cutscene_line_index = 0
        self.engine.change_state(GameState.CUTSCENE)
    def load_scenes(self):
        """Load cutscene data from cutscene.json"""
        cutscene_file = "cutscene.json"
        cutscene_file = os.path.join(EVENT_DIR, cutscene_file)
        if os.path.exists(cutscene_file):
            try:
                with open(cutscene_file, 'r') as f:
                    self.cutscenes = json.load(f)
            except Exception as e:
                print(f"Error loading dialog file: {e}")
                self.cutscenes = {}
        else:
            # Create default dialog file
            pass
    def get_current_line(self):
        """Get the current line of dialog"""
        if self.cutscene and self.current_line_index < len(self.cutscene):
            return self.cutscene[self.current_line_index]
        return ""
    def advance_scene(self):
        """Advance to the next line of dialog"""
        self.current_line_index += 1
        if self.get_current_line() == "back_to_main_menu":
            self.current_line_index = len(self.cutscene)
            self.engine.previous_state = GameState.MAIN_MENU
            self.engine.party.empty_party()
            self.engine.maps = []
        if self.current_line_index < len(self.cutscene) - 1:
            return True
        else:
            # Reached end of current dialog, now await user input
            self.awaiting_input = True
            self.user_input = ""
            return False
    def end_scene(self):
        """End the current dialog"""
        self.current_lines = []
        self.current_line_index = 0