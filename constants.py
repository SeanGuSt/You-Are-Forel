from enum import Enum
from functools import wraps
import time
# Constants
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 700
TILE_SIZE = 32
TILE_WIDTH = TILE_SIZE
TILE_HEIGHT = TILE_SIZE
MAP_WIDTH = 18
MAP_VIEW_WIDTH = TILE_WIDTH * MAP_WIDTH
MAP_HEIGHT = 16
MAP_VIEW_HEIGHT = TILE_HEIGHT * MAP_HEIGHT
DEFAULT_INPUT_REPEAT_DELAY = 300
DEFAULT_INPUT_REPEAT_INTERVAL = 300
DEFAULT_PLAYER_MOVE_FRAMES = 16
DEFAULT_MOVEMENT_PENALTY = 1
DEFAULT_WAIT_PENALTY = 2
DEFAULT_OVERWORLD_MOVEMENT_PENALTY = 5
# Directories
MAPS_DIR = "maps"
SAVES_DIR = "saves"
SOUNDS_DIR = "sound"
ITEMS_DIR = "items"
OBJS_DIR = "objects"
TALK_DIR = "dialog"
QUEST_DIR = "quests"
EVENT_DIR = "events"
IMAGE_DIR = "sprites"


GAME_TITLE = "You are Forel"
NEW_GAME_SPAWNER = "new_game_spawner"
# Colors
DARK_GRAY = (64, 64, 64)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
PINK = (255, 192, 203)
BROWN = (181, 101, 29)
GRAY = (128, 128, 128)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LIME = (191, 255, 0)
OLIVE = (128, 128, 0)
MAROON = (128, 0, 0)
NAVY = (0, 0, 128)
TEAL = (0, 128, 128)
AQUA = (0, 255, 200)
VIOLET = (238, 130, 238)
INDIGO = (75, 0, 130)
SALMON = (250, 128, 114)
TURQUOISE = (64, 224, 208)
TAN = (210, 180, 140)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
CORAL = (255, 127, 80)
CHOCOLATE = (210, 105, 30)
PLUM = (221, 160, 221)
MINT = (189, 252, 201)
PEACH = (255, 218, 185)
LAVENDER = (230, 230, 250)
BEIGE = (245, 245, 220)
SKY_BLUE = (135, 206, 235)
LIGHT_GREEN = (144, 238, 144)
DARK_GREEN = (0, 100, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)
RUST = (183, 65, 14)
AMBER = (255, 191, 0)
CRIMSON = (220, 20, 60)
IVORY = (255, 255, 240)
CHARCOAL = (54, 69, 79)
MOSS = (138, 154, 91)
SAND = (194, 178, 128)
DENIM = (21, 96, 189)
BRICK = (178, 34, 34)
FOREST = (34, 139, 34)
FLAME = (226, 88, 34)
ICE = (173, 216, 230)
ROYAL_BLUE = (65, 105, 225)

class GameState(Enum):
    MAIN_MENU = 0
    OVERWORLD = 1
    TOWN = 2
    COMBAT = 3
    MENU_STATS = 4
    MENU_INVENTORY = 5
    MENU_EQUIPMENT = 6
    MENU_OPTIONS = 7
    MENU_SAVE_LOAD = 8
    MENU_QUEST_LOG = 9
    DIALOG = 10 # New state for dialog
    CUTSCENE = 11
    EVENT = 12

class ObjectState(Enum):
    WALK = "walk"
    STAND = "stand"
    SELL = "sell"#A state to ensure merchants can't try to sell to you while they want to kill you.
    SLEEP = "sleep"#Disables the ability to talk to the object
    PATROL = "patrol"
    PURSUE = "pursue"
    ATTACK_MELEE = "attack_melee"
    ATTACK_RANGE = "attack_range"
    KEEP_MOVING = "keep_moving"

class TileType(Enum):
    GRASS = '.'
    WATER = '~'
    MOUNTAIN = '^'
    FOREST = 'T'
    TOWN = 'C'
    DUNGEON = 'D'
    FLOOR = '_'
    WALL = '#'
    DOOR = '+'

class VirtueType(Enum):
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    EARTH = "earth"
    WATER = "water"
    WIND = "wind"
    LAVA = "lava"
    NATURE = "nature"

class OverusePenalty(Enum):
    NONE = "none"
    STAT_REDUCTION = "stat_reduction"
    HP_DAMAGE = "hp_damage"
    ACCURACY_REDUCTION = "accuracy_reduction"
    SPELL_FAILURE = "spell_failure"
    MOVEMENT_REDUCTION = "movement_reduction"

class DamageType(Enum):
    HOLY = "holy"
    STRIKE = "strike"
    SLASH = "slash"
    STAB = "stab"
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    WIND = "wind"
    NATURE = "nature"
    LAVA = "lava"
    ICE = "ice"
    LIGHTNING = "lightning"
    POISON = "poison"

class Direction(Enum):
    NORTH = (0, -1)
    NORTHEAST = (1, -1)
    EAST = (1, 0)
    SOUTHEAST = (1, 1)
    SOUTH = (0, 1)
    SOUTHWEST = (-1, 1)
    WEST = (-1, 0)
    NORTHWEST = (-1, -1)
    WAIT = (0, 0)

class ObjectType(Enum):
    ITEM = "item"
    NPC = "npc"
    MONSTER = "monster"
    TELEPORTER = "teleporter"
    TRIGGER = "trigger"
    DESTRUCTIBLE = "destructible"
    CHEST = "chest"
    NODE = "node"

class EquipmentSlot(Enum):
    WEAPON = "weapon_melee"
    RANGED = "weapon_ranged"
    ARMOR = "armor"
    # Expandable for future equipment types
    SHIELD = "shield"
    ACCESSORY = "accessory"
    """
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    ACCESSORY_1 = "accessory_1"
    ACCESSORY_2 = "accessory_2"
    """

class TargetType(Enum):
    TARGET = "target"
    DIRECTION = "direction"

class EffectType(Enum):
    STAT_BUFF = "stat_buff"
    DAMAGE = "damage"
    HEAL = "heal"
    ON_ATTACK_HEAL = "on_attack_heal"
    ON_DEFEND_DAMAGE = "on_defend_damage"
    ON_KILL_BONUS = "on_kill_bonus"
    CHANGE_SPRITE = "change_sprite"
    # Expandable for future effects


class EffectTrigger(Enum):
    PASSIVE = "passive"
    ON_ATTACK = "on_attack"
    ON_DEFEND = "on_defend"
    ON_KILL = "on_kill"
    ON_EQUIP = "on_equip"
    ON_UNEQUIP = "on_unequip"
    ON_USE = "on_use"

def time_function(label=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            duration = (end - start) * 1000  # ms
            print(f"[TIME] {label or func.__name__} took {duration:.3f} ms")
            return result
        return wrapper
    return decorator
