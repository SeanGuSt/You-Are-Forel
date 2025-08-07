import os
import json
from typing import TYPE_CHECKING
from objects.characters import Party
from objects.map_objects import MapObject
from objects.object_basics import ElevatorHelper
from dialog.dialog_helpers import *
from constants import TALK_DIR
import re
if TYPE_CHECKING:
    from ultimalike import GameEngine

# New Dialog Manager class
class DialogManager:
    def __init__(self, engine: 'GameEngine'):
        self.dialogs = {}
        self.load_dialogs()
        self.dialog_key = ""
        self.current_dialog = None
        self.current_speaker = None
        self.current_lines = []
        self.npc_vocab = {}
        self._config_words = ["elevator_config"]
        self.engine = engine
        self.looking = False
        self.current_line_index = 0
        self.user_input = ""
        self.last_input = ""
        self.cursor_blink = 0
        self.awaiting_input = False
        
        
    def load_dialogs(self):
        """Load dialog data from dialog.json files"""
        onlyfiles = [f for f in os.listdir(TALK_DIR) if os.path.isfile(os.path.join(TALK_DIR, f))]
        for file_name in onlyfiles:
            if file_name.endswith("dialog.json"):
                with open(os.path.join(TALK_DIR, file_name), 'r') as f:
                    dialogs = json.load(f)
                    if dialogs:
                        for key, value in dialogs.items():
                            self.dialogs[key] = value

    def start_dialog(self, npc: MapObject):
        """Start a dialog with a map object"""
        # Get the NPC name from object args
        npc_name = npc.args.get("name", "").lower()
        dialog_key = npc.args.get("dialog_key", npc_name)
        
        if dialog_key not in self.dialogs:
            print(f"cannot find key {dialog_key}")
            return False  # Cannot talk to this object
        self.engine.event_manager.talked_to_npcs.add(self.dialog_key)
        
        self.current_speaker = npc
        npc_id = f"{dialog_key}"
        self.dialog_key = npc_id
        
        # Determine which greeting to use
        self.user_input = "__hi__"
        
        # Get the greeting dialog
        dialog_data = self.dialogs[dialog_key]
        if self.user_input in dialog_data:
            self.process_user_input()
        else:
            self.current_lines = ["Hello."]
        print(self.current_lines)
        self.current_line_index = 0
        self.user_input = ""
        self.awaiting_input = True if len(self.current_lines) == 1 else False
        self.cursor_blink = 0
        return True
    
    def start_looking(self, obj: MapObject):
        self.current_speaker = obj
        if obj.look_text:
            self.current_lines = obj.look_text
        else:
            self.current_lines = [f"Nothing but a boring old {obj.name}."]
        self.looking = True
        return True

    def advance_looking(self):
        self.current_line_index += 1
        if self.current_line_index < len(self.current_lines):
            return True
        return False
    def advance_dialog(self):
        """Advance to the next line of dialog"""
        check = True
        while check:
            self.current_line_index += 1
            check = "=" in self.get_current_line()
            if check:
                self._do_event(self.get_current_line())
                continue
            if self.current_line_index < len(self.current_lines) - 1:
                return True
            else:
                check = False
                
        # Reached end of current dialog, now await user input
        self.awaiting_input = True
        self.user_input = ""
        return False
    
    def process_user_input(self):
        npc = self.current_speaker
        if not npc:
            return
        input_text = self.user_input
        self.current_line_index = 0
        npc_name = npc.args.get("name", "").lower()
        dialog_key = npc.args.get("dialog_key", npc_name)
        dialog_data = self.dialogs.get(dialog_key, {})

        input_lower = input_text.lower().strip()

        if input_lower in self._config_words:
            input_lower = "bleh"

        aliases = dialog_data.get("aliases", {})
        contextual_aliases = dialog_data.get("contextual_aliases", {})
        if input_lower in contextual_aliases.get(self.last_input, {}):
            input_lower = contextual_aliases[self.last_input][input_lower]

        if npc.__is__(ElevatorHelper):
            config = npc.args.get("elevator_config", {}) or dialog_data.get("elevator_config", {})
            current_map = self.engine.current_map.name

            if input_lower == "elevator":
                self.current_lines = generate_elevator_text(config, current_map)
                if not "seen_red_text_tutorial" in self.engine.event_manager.flags:
                    self.engine.event_manager.flags.add("seen_red_text_tutorial")
                    self.current_lines[-1] += "(Type keywords to continue a conversation. Most keywords will be highlighted in red.)"
                self.awaiting_input = True
                self.last_input = input_lower  # <- track last keyword
                self.user_input = ""
                return
            aliases = config.get("aliases", {})
            # Resolve alias if it exists
            input_lower = aliases.get(input_lower, input_lower)
            contextual_aliases = config.get("contextual_aliases", {})
            if input_lower in contextual_aliases.get(self.last_input, {}):
                input_lower = contextual_aliases[self.last_input][input_lower]
            if input_lower in config.get("destinations", {}):
                response = get_destination_response(config, input_lower, current_map)
                self.current_lines = response["text"]
                self.engine.event_manager.pending_events = response.get("events", {})
                self.awaiting_input = True
                self.last_input = input_lower  # <- track last keyword
                self.user_input = ""
                return

        # Try exact match
        responses = dialog_data.get(input_lower, [])

        # Fallback: if fluent, try translating player input into foreign word
        if not responses and self.engine.party.god_favor > 3:
            # Check if player typed English that maps to a foreign word
            npc_vocab = self.npc_vocab.get(npc_name, {})  # e.g., jack_knight_vocab
            english_to_foreign = {v: k for k, v in npc_vocab.items()}
            foreign_guess = english_to_foreign.get(input_lower)
            if foreign_guess:
                responses = dialog_data.get(foreign_guess, [])
        selected = None

        for entry in responses:
            conditions = entry.get("conditions", [])
            if all(self._check_condition(cond) for cond in conditions):
                selected = entry["text"]
                for flag in entry.get("set_flags", []):
                    self.engine.event_manager.flags.add(flag)
                for event in entry.get("events", []):
                    self._do_event(event)
                break

        if not selected:
            selected = ["Huh?"]
        else:
            self.last_input = input_lower  # <- track last keyword

        if self.engine.party.god_favor > 3 and any("english" in entry for entry in responses):
            # Find the matching response again and use the english line
            for entry in responses:
                if all(self._check_condition(cond) for cond in entry.get("conditions", [])):
                    selected = entry.get("english", entry["text"])
                    break
        else:
            selected = [self._translate_line(line) for line in selected]

        self.current_lines = selected
        self.awaiting_input = True if len(self.current_lines) == 1 else False
        
        self.user_input = ""
        return input_lower
    
    def _check_condition(self, condition: str) -> bool:
        return self.engine.event_manager._check_condition(condition)
    
    def _do_event(self, event: str):
        return self.engine.event_manager._do_event(event)
    
    def _translate_line(self, line: str) -> str:
        if self.engine.party.god_favor > 3:
            return line  # Just in case this gets called erroneously
        def translate_word(word: str):
            prefix = re.match(r"^\W*", word).group()
            suffix = re.match(r".*?(\W*)$", word).group(1)
            core = word.strip(".,!¿?\"").lower()
            translated = self.engine.party.foreign_word_dict.get(core, None)
            return f"{prefix}{translated if translated else word}{suffix}"

        return " ".join(translate_word(word) for word in line.split())
    
    def get_current_line(self):
        """Get the current line of dialog"""
        if self.current_lines and self.current_line_index < len(self.current_lines):
            current_line = self.current_lines[self.current_line_index]
            if "{time_of_day}" in current_line:
                current_line = format_time_of_day(current_line, self.engine.schedule_manager.current_game_time)
            return current_line
        return ""
    
    def is_dialog_finished(self):
        """Check if we're at the end of a dialog sequence and awaiting input"""
        return self.awaiting_input
    
    def end_dialog(self):
        """End the current dialog"""
        self.current_dialog = None
        self.engine.event_manager.force_end = False
        self.current_speaker = None
        self.current_lines = []
        self.current_line_index = 0
        self.user_input = ""
        self.awaiting_input = False
        self.looking = False
        for tl in self.engine.event_manager.timer_limits:
            self.engine.event_manager.timer_limits[tl] = 0
    
    