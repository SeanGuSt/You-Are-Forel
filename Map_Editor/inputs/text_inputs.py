from typing import TYPE_CHECKING
import ast
import pygame
from Map_Editor.me_constants import EditState
if TYPE_CHECKING:
    from Map_Editor.map_editor import MapEditor
def input_new_tile_inputs(self: 'MapEditor', event):
    match event.key:
        case pygame.K_RETURN:
            if self.input0 and self.input1:#first and second lines
                match self.previous_state:
                    case EditState.TILE:
                        if self.input0 in self.char_list:
                            print("Please choose a unique tile representative.")
                            return
                        if self.input1 not in self.tdb.tiles:
                            print(f"{self.input1} is not a valid tile.")
                            return
                        self.tile_map[self.input0] = self.input1
                        char_list = list(self.tile_map.keys())
                        self.state = EditState.TILE
                        self.input_field = 0
                        self.input1 = ""
        case pygame.K_ESCAPE:
            self.state = self.previous_state
            self.input_field = 0
            self.input1 = ""
        case pygame.K_BACKSPACE:
            if self.input1 and self.input_field == 1:
                self.input1 = self.input1[:-1]
            elif self.input0 and self.input_field == 0:
                input0 = input0[:-1]
        case pygame.K_TAB:
            self.input_field = 1 - self.input_field  # Toggle between 0 and 1
        case _:
            if self.input_field == 0 and len(self.input0) < 1:
                self.input0 += event.unicode
            elif self.input_field == 1 and len(self.input1) < 20:
                self.input1 += event.unicode
def input_new_objects_inputs(self: 'MapEditor', event):
    match event.key:
        case pygame.K_RETURN:
            self.input_field = 0
            if self.input0 and self.input1:
                split_input0 = self.input0.split("__")
                def recursive_dicts(big_dict, split_input: list[str], input1: str):
                    if len(split_input) > 1:
                        sp0 = split_input[0]
                        sp1 = split_input[1:]
                        if sp0 not in big_dict:
                            big_dict[sp0] = {}
                        recursive_dicts(big_dict[sp0], sp1, input1)
                    elif "[" in input1 and "]" in input1:
                        big_dict[split_input[0]] = ast.literal_eval(input1)
                    else:
                        try:
                            big_dict[split_input[0]] = int(input1)
                        except:
                            big_dict[split_input[0]] = input1
                recursive_dicts(self.arg_input_args, split_input0, self.input1)
                self.input0 = ""
                self.input1 = ""
            else:
                if self.pending_object:
                    if "name" not in self.arg_input_args:
                        print("Please include a name at minimum")
                        self.input0 = "name"
                        return
                    name = self.arg_input_args.pop("name")
                    self.pending_object["args"] = self.arg_input_args
                    self.objects_data[name] = self.pending_object
                self.arg_input_args = {}
                self.input0 = ""
                self.input1 = ""
                self.pending_object = None
        case pygame.K_ESCAPE:
            self.arg_input_args = {}
            self.input0 = ""
            self.input1 = ""
            self.pending_object = None
            self.revert_state()
        case pygame.K_BACKSPACE:
            if self.input_field == 1 and self.input1:
                self.input1 = self.input1[:-1]
            elif self.input_field == 0 and self.input0:
                self.input0 = self.input0[:-1]
        case pygame.K_TAB:
            self.input_field = 1 - self.input_field  # Toggle between 0 and 1
        case _:
            if self.input_field == 0 and len(self.input0) < 40:
                self.input0 += event.unicode
            elif self.input_field == 1 and len(self.input1) < 160:
                self.input1 += self.event.unicode