from tiles.tiles import Tile
from constants import *
from objects.characters import Character

class Grass(Tile):
    color = (34, 139, 34)

class Water(Tile):
    color = (0, 100, 200)
    is_passable = False

class Floor(Tile):
    step_sound = "wood_footstep"
    color = (222, 184, 135)

class FloorCarpet(Floor):
    step_sound = "carpet_footstep"

class FloorCarpetBlue(FloorCarpet):
    color = LIGHT_BLUE

class FloorCarpetRed(FloorCarpet):
    color = RED

class FloorSoil(Floor):
    color = (146, 116, 91)

class FloorStone(Floor):
    color = GRAY

class FloorWood(Floor):
    color = (146, 60, 91)

class Mountain(Tile):
    color = DARK_GRAY
    is_passable = False
    can_see_thru = False

class Sky(Tile):
    color = SKY_BLUE
    is_passable = False

class Stairs(Tile):
    color = BEIGE

class Walkway(Tile):
    pass

class TargetTile(Tile):
    color = WHITE

class AreaTile(Tile):
    color = BLACK

class WalkwayCobblestone(Walkway):
    color = (195, 191, 191)

class Wall(Tile):
    color = GRAY
    is_passable = False
    can_see_thru = False

class Rail(Wall):
    color = BROWN
    can_see_thru = True

class WallBrick(Wall):
    color = BRICK

class FakeHaremWallBrick(WallBrick):
    is_passable = True

class WallBrickTorch(WallBrick):
    pass

class WallWood(Wall):
    color = (91, 39, 11)