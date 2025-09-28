import os, json
from constants import GameState, EVENT_DIR
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ultimalike import GameEngine
class CutsceneManager:
    def __init__(self, engine: 'GameEngine'):
        self.cutscenes: dict = {}
        self.cutscene: list = []
        self.current_image = None
        self.engine = engine
        self.load_scenes()
        self.current_line_index: int = 0
    def start_scene(self, cutscene_id: str):
        if cutscene_id not in self.cutscenes:
            print(f"Cannot find {cutscene_id}")
            return False
        if self.engine.state == GameState.DIALOG:
            #If the dialog has lines left when the event is started, only start an event, don't end the dialog.
            if self.engine.dialog_manager.current_line_index >= len(self.engine.dialog_manager.current_lines) - 1:
                self.engine.dialog_manager.end_dialog()
        elif self.engine.state == GameState.EVENT:
            #If the cutscene has lines left, don't end the cutscene.
            if self.engine.event_manager.current_index >= len(self.engine.event_manager.current_event_queue["script"]) - 1:
                self.engine.event_manager.end_event()
        self.cutscene = self.cutscenes[cutscene_id]
        self.cutscene_line_index = -1
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
        """Get the current line of the cutscene"""
        if self.cutscene and self.current_line_index < len(self.cutscene):
            return self.cutscene[self.current_line_index]
        return ""
    def advance_scene(self):
        """Advance to the next line of the cutscene"""
        self.current_line_index += 1
        if self.get_current_line() == "back_to_main_menu":
            self.current_line_index = len(self.cutscene)
            self.engine.revert_state()
            self.engine.party.empty_party()
            self.engine.maps = []
        if "new_slide" in self.get_current_line():
            _, new_slide = self.get_current_line().split("=")
            self.engine.sprite_db.get_slide(new_slide)
            self.current_line_index += 1
        if self.current_line_index <= len(self.cutscene) - 1:
            return True
        else:
            return False
    def end_scene(self):
        """End the current dialog"""
        self.current_lines = []
        self.current_image = None
        self.current_line_index = 0