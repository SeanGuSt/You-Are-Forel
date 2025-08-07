from typing import TYPE_CHECKING
import copy
if TYPE_CHECKING:
    from Map_Editor.map_editor import MapEditor

def snapshot(self: 'MapEditor'):
    return {
        "ascii_map": copy.deepcopy(self.ascii_map),
        "objects_data": copy.deepcopy(self.objects_data)
    }
def apply_snapshot(self: 'MapEditor'):
    state = self.undo_stack.pop()
    self.ascii_map = copy.deepcopy(state["ascii_map"])
    self.objects_data = copy.deepcopy(state["objects_data"])

def undo(self: 'MapEditor'):
    if self.undo_stack:
        self.redo_stack.append(snapshot(self))
        apply_snapshot(self)

def redo(self: 'MapEditor'):
    if self.redo_stack:
        pass
def record_additions(self: 'MapEditor'):
    self.undo_stack.append(snapshot(self))
    self.redo_stack.clear()