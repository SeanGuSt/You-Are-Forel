from typing import TYPE_CHECKING
import copy
import pygame
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

def increase_level(self: 'MapEditor', tx: int, ty:int, mods):
    self.levels_map[ty][tx] += 1
    if self.levels_map[ty][tx] > 9:
        self.levels_map[ty][tx] = 1
    if mods & pygame.KMOD_CTRL:
        for y in range(len(self.ascii_map)):
            for x in range(len(self.ascii_map[0])):
                if self.ascii_map[y][x] == self.ascii_map[ty][tx]:
                    self.levels_map[y][x] = self.levels_map[ty][tx]


def decrease_level(self: 'MapEditor', tx: int, ty:int, mods):
    self.levels_map[ty][tx] -= 1
    if self.levels_map[ty][tx] < 1:
        self.levels_map[ty][tx] = 9
    if mods & pygame.KMOD_CTRL:
        for y in range(len(self.ascii_map)):
            for x in range(len(self.ascii_map[0])):
                if self.ascii_map[y][x] == self.ascii_map[ty][tx]:
                    self.levels_map[y][x] = self.levels_map[ty][tx]