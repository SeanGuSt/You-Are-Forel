import os
import json
from typing import TYPE_CHECKING
from objects.characters import Party
from objects.map_objects import MapObject
from objects.nodegroup import NodeGroup
from objects.object_basics import ElevatorHelper, Merchant
from dialog.dialog_helpers import *
from constants import TALK_DIR, GameState, ObjectState
import re
if TYPE_CHECKING:
    from ultimalike import GameEngine

# New Dialog Manager class
class DialogManager:
    def __init__(self, engine: 'GameEngine'):
        self.dialogs = {}
        self.load_dialogs()
        self.dialog_key = ""
        self._merge_cache = {}
        self.current_dialog = None
        self.current_speaker = None
        self.current_lines = []
        self.current_line = ""
        self.scare_counter = 0
        self.npc_vocab = {}
        self._config_words = ["elevator_config"]
        self.engine = engine
        self.looking = False
        self.current_line_index = 0
        self.user_input = ""
        self.last_input = ""
        self.cursor_blink = 0
        self.awaiting_keyword = False
        self.waiting_for_input = False
        
        
    def load_dialogs(self):
        """Load dialog data from dialog.json files"""
        onlyfiles = [f for f in os.listdir(TALK_DIR) if os.path.isfile(os.path.join(TALK_DIR, f))]
        for file_name in onlyfiles:
            if file_name.endswith("dialog.json"):
                with open(os.path.join(TALK_DIR, file_name), 'r') as f:
                    dialogs = json.load(f)
                    if dialogs:
                        for dialog_key, dialog_dict in dialogs.items():
                            self.dialogs[dialog_key] = dialog_dict

    def get_dialog_data(self, dialog_key: str) -> dict | None:
        """Resolve dialog inheritance dynamically (multi-step)."""
        if dialog_key in self._merge_cache:
            return self._merge_cache[dialog_key]

        if dialog_key not in self.dialogs:
            return None

        data = self.dialogs[dialog_key]
        parts = dialog_key.split("#")
        if len(parts) > 1:
            # Reconstruct hierarchy step by step
            base_key = parts[0]
            merged = self.get_dialog_data(base_key) or {}
            for i in range(1, len(parts)):
                variant_key = "#".join(parts[:i+1])
                if variant_key in self.dialogs:
                    merged = merge_dialogs(merged, self.dialogs[variant_key])
            self._merge_cache[dialog_key] = merged
            return merged

        # Base dialog, no inheritance
        return data

    def start_dialog(self, npc: MapObject):
        """Start a dialog with a map object"""
        # Get the NPC name from object args

        if npc.state == ObjectState.SLEEP:
            return False
        if npc.group and npc.group.speaker_node and "dialog_key" not in npc.args:
            npc = npc.group.speaker_node#This way, only one node out of a group needs the dialog key.
        npc_name = npc.args.get("name", "").lower()
        dialog_key = npc.args.get("dialog_key", npc_name)
        dialog_data = self.get_dialog_data(dialog_key)
        if not dialog_data:
            print(f"cannot find key {dialog_key}")
            return False
        self.engine.event_manager.talked_to_npcs.add(self.dialog_key)
        
        self.current_speaker = npc
        self.current_speaker.state = ObjectState.TALK
        npc_id = f"{dialog_key}"
        self.dialog_key = npc_id
        
        # Determine which greeting to use
        self.user_input = "__hi__"
        
        # Get the greeting dialog
        if self.user_input in dialog_data:
            self.process_user_input()
        else:
            self.current_lines = ["Hello."]
        self.current_line_index = -1
        self.advance_dialog()
        self.user_input = ""
        self.awaiting_keyword = True if len(self.current_lines) == 1 else False
        self.waiting_for_input = True
        self.cursor_blink = 0
        return True
    
    def start_looking(self, obj: MapObject):
        if obj.look_text:
            self.current_speaker = obj
            self.current_lines = obj.look_text
            self.current_line_index = 0
            self.current_line = self.get_current_line()
            self.looking = True
            self.waiting_for_input = True
            return True
        return False
        
    def advance_dialog(self):
        """Advance to the next line of dialog or perform the next event"""
        if not self.current_lines or self.waiting_for_input or self.awaiting_keyword or self.engine.event_manager.walkers:
            return
        if self.engine.event_manager.timer_manager.get_remaining_time("event_pause") > 0:
            return
        self.current_line_index += 1
        if self.current_line_index >= len(self.current_lines)-1:
            if self.engine.event_manager.force_end:
                self.end_dialog()
                return
            elif not self.looking:
                self.waiting_for_input = True
                self.awaiting_keyword = True
                self.user_input = ""
            elif self.looking and self.current_line_index >= len(self.current_lines):
                self.end_dialog()
        current_line = self.get_current_line()
        use_line = True
        has_cond = "++" in current_line
        if has_cond:
            condition, current_line = current_line.split("++") 
            use_line = self._check_condition(condition)
        if use_line:
            is_event = "=" in current_line
            if is_event:
                self._do_event(current_line)
                if self.engine.event_manager.force_end and self.current_line_index >= len(self.current_lines)-1:#In case jump occurred
                    self.end_dialog()
            else:
                self.current_line = current_line
                self.waiting_for_input = True
                
        # Reached end of current dialog, now await user input
        
    
    def process_user_input(self):
        print(self.user_input)
        npc = self.current_speaker
        if not npc:
            return
        input_text = self.user_input
        self.current_line_index = 0
        npc_name = npc.args.get("name", "").lower()
        dialog_key = npc.args.get("dialog_key", npc_name)
        dialog_data = self._merge_cache.get(dialog_key, self.dialogs.get(dialog_key, {}))
        

        input_lower = input_text.lower().strip()

        aliases = dialog_data.get("aliases", {})
        contextual_aliases = dialog_data.get("contextual_aliases", {})
        if input_lower in contextual_aliases.get(self.last_input, {}):
            input_lower = contextual_aliases[self.last_input][input_lower]
        if input_lower in aliases:
            input_lower = aliases[input_lower]

        if input_lower in self._config_words:
            input_lower = "bleh"
        if input_lower == "show":
            self.engine.picking_item_to_show = True
            self.engine.change_state(GameState.MENU_INVENTORY)
            return
        elif "show" in input_lower:
            item_name = input_lower[5:]
            print(item_name)
            if not self.engine.party.check_for_item_by_name(item_name):
                self.current_lines = [f"(You don't have {item_name}.)"]
                self.current_line_index = 0
                self.current_line = self.get_current_line()
                return
        if input_lower == "shop":
            if self.current_speaker.__is__(Merchant):
                self.engine.change_state(GameState.MENU_SHOPPING)
                self.user_input = ""
                return
        if input_lower == "bye":
            self.end_dialog()
            return
        self.current_speaker.state = ObjectState.TALK

        if npc.__is__(ElevatorHelper):
            config = npc.args.get("elevator_config", {}) or dialog_data.get("elevator_config", {})
            current_map = self.engine.current_map.name

            if input_lower == "elevator":
                self.current_lines = generate_elevator_text(config, current_map)
                if not "seen_red_text_tutorial" in self.engine.event_manager.flags:
                    self.engine.event_manager.flags.add("seen_red_text_tutorial")
                    self.current_lines[-1] += "(Type keywords to continue a conversation. Most keywords will be highlighted in red.)"
                self.awaiting_keyword = True
                self.last_input = input_lower  # <- track last keyword
                self.user_input = ""
                current_line = self.get_current_line()
                has_cond = "++" in current_line
                use_line = True
                if has_cond:
                    condition, current_line = current_line.split("++") 
                    use_line = self._check_condition(condition)
                if use_line:
                    is_event = "=" in current_line
                    if is_event:
                        self._do_event(current_line)
                    else:
                        self.current_line = current_line
                        self.waiting_for_input = True
                return
            aliases = config.get("aliases", {})
            # Resolve alias if it exists
            input_lower = aliases.get(input_lower, input_lower)
            contextual_aliases = config.get("contextual_aliases", {})
            if input_lower in contextual_aliases.get(self.last_input, {}):
                input_lower = contextual_aliases[self.last_input][input_lower]
            if input_lower in config.get("destinations", {}):
                response = get_destination_response(config, input_lower, current_map)
                self.current_lines = response["script"]
                self.engine.event_manager.pending_events = response.get("events", {})
                self.awaiting_keyword = True
                self.waiting_for_input = True
                self.last_input = input_lower  # <- track last keyword
                self.user_input = ""
                self.current_line = self.get_current_line()
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
                selected = entry["script"]
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
                    selected = entry.get("english", entry["script"])
                    break
        else:
            selected = [self._translate_line(line) for line in selected]

        self.current_lines = selected
        self.current_line = self.get_current_line()
        self.awaiting_keyword = True if len(self.current_lines) == 1 else False
        
        self.user_input = ""
        return input_lower
    
    def _check_condition(self, condition: str) -> bool:
        return self.engine.event_manager._check_condition(condition)
    
    def format_text(self, text: str = ""):
        if not text:
            text = self.current_lines[self.current_line_index]
        while True:
            start_index = text.find("{")
            end_index = text.find("}", start_index + 1)
            if start_index < 0 or end_index < 0:
                return text
            formattable_chunk = text[start_index:(end_index+1)]
            match formattable_chunk:
                case "{time_of_day}":
                    text = format_time_of_day(text, self.engine.schedule_manager.current_game_time)
                case _:
                    text = text.replace(formattable_chunk, "", 1)
                    formattable_chunk = formattable_chunk[1:-1]
                    #since formattable_chunk was removed, start_index should be the new home of {+
                    if not text[start_index:(start_index+2)] == "{+":
                        raise SyntaxError(f"Conditionals like {formattable_chunk}" +  "must have a positive result included immediately after, between {+ and +}")
                    end_index = text.find("+}", start_index + 1)
                    if end_index < 0:
                        raise SyntaxError("Conditionals' positive results must end with +}")
                    if len(text) >= end_index + 3:
                        #Make sure this negative option belongs to this specific conditional
                        negative_option = text[(end_index+1):(end_index+3)] == "{-"
                    if self._check_condition(formattable_chunk):
                        text = text.replace(text[start_index:(end_index+2)], text[(start_index+2):end_index])
                        if negative_option:
                            #We know 4 characters,{++}, were removed, so the "{" of "{-" moved to end_index-3
                            start_index = end_index - 3
                            end_index = text.find("-}", start_index+2)
                            if end_index < 0:
                                raise SyntaxError("Conditionals' negative results must end with -}")
                            text = text.replace(text[start_index:(end_index+2)], "", 1)
                    else:
                        text = text.replace(text[start_index:(end_index+1)], "", 1)
                        if negative_option:
                            #We know where the start is for both if-else cases now, so no need to recalculate the start_index
                            end_index = text.find("-}", start_index+2)
                            if end_index < 0:
                                raise SyntaxError("Conditionals' negative results must end with -}")
                            text = text.replace(text[start_index:(end_index+2)], text[(start_index+2):end_index])



                    
            
    
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
            current_line = self.format_text()
            return current_line
        return ""
    
    def is_dialog_finished(self):
        """Check if we're at the end of a dialog sequence and awaiting input"""
        return self.awaiting_keyword
    
    def end_dialog(self):
        """End the current dialog"""
        self.current_dialog = None
        self.engine.event_manager.force_end = False
        self.current_speaker = None
        self.current_lines = []
        self.current_line_index = 0
        self.current_line = ""
        self.user_input = ""
        self.waiting_for_input = False
        self.awaiting_keyword = False
        self.looking = False
        self.engine.revert_state()

def merge_dialogs(base: dict, overrides: dict) -> dict:
    """Merge override dialog entries into a base dict, returning new dict."""
    result = dict(base)  # shallow copy

    for key, value in overrides.items():
        if key.startswith("-"):
            # Remove entry
            to_remove = key[1:]
            result.pop(to_remove, None)
            continue

        if key.endswith("+"):
            # Append mode
            target_key = key[:-1]
            if target_key in result and isinstance(result[target_key], list) and isinstance(value, list):
                result[target_key] = result[target_key] + value
            else:
                # If base doesn’t exist, just set it
                result[target_key] = value
            continue

        # Default: replace
        result[key] = value
    return result
    
    