import os
from dataclasses import dataclass, asdict, fields, MISSING
import random
import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from tiles.tiles import Tile
from tiles.tile_database import TileDatabase
from constants import *
import copy
from objects.characters import Character
from objects.object_templates import Node, Monster, MapObject, Teleporter, Chest, NPC, ItemHolder, NODE_REGISTRY
from objects.object_basics import BedBasic, BedRoyal, DoorBasic
from objects.nodegroup import NodeGroup
import objects.monsters
import objects.projectiles
import objects.npcs
#from map_objects import MapObject  # for circular dep. resolution if needed
if TYPE_CHECKING:
    from ultimalike import GameEngine

class MapObjectDatabase:
    def __init__(self, engine: 'GameEngine'):
        self.obj_templates = NODE_REGISTRY
        self.engine = engine
    
    def create_obj(self, obj_name: str, obj_type: str, new_properties: dict[str, Any]):

        cls = self.obj_templates.get(obj_type, None)
        if cls:
            if "object_type" not in new_properties:
                new_properties["object_type"] = obj_type
            new_properties["name"] = obj_name
            cls_instance = cls.from_dict(new_properties, self.engine)
            return cls_instance
        return None

class Map:
    def __init__(self, width: int, height: int, engine: 'GameEngine', name: str = ""):
        self.width = width
        self.height = height
        self.name = name
        self.generation = 0
        self.engine = engine
        self.tiles = [[None for _ in range(width)] for _ in range(height)]
        self.tiles_default = [[None for _ in range(width)] for _ in range(height)]
        self.objects: List[Node] = []
        self.objects_by_layer: dict[int, list[Node]] = {}
        self.groups: dict[str, NodeGroup] = {}
        self.adjacent_maps: Dict[str, str] = {}
        self.enemy_positions = {}
        
    def get_tile_lower(self, pos: tuple[int, int]) -> Optional[Tile]:
        x, y = pos
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return False  # Default impassable boundary
        
    def set_tile(self, pos: tuple[int, int], tile: Tile, and_default: bool = False):
        x, y = pos
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile
            if and_default:
                self.tiles_default[y][x] = tile
    
    def set_tile_by_name(self, pos: tuple[int, int], tile_name: str, tile_db: TileDatabase, and_default: bool = False):
        tile = tile_db.get_tile(tile_name)
        if tile:
            self.set_tile(pos, tile, and_default)
    
    def revert_tile(self, pos: tuple[int, int]):
        self.set_tile(pos, copy.deepcopy(self.tiles_default[pos[1]][pos[0]]))

    def revert_map_tiles(self):
        self.tiles = copy.deepcopy(self.tiles_default)
            
    def is_passable(self, pos: tuple[int, int], old_tile: Tile | tuple[int, int] = None) -> bool:
        tile = self.get_tile_lower(pos)
        if not tile:
            return False
        if old_tile and old_tile is not Tile:
            old_tile = self.get_tile_lower(old_tile)
        terrain_check = tile.can_pass_thru(old_tile)
        if not terrain_check:
            return False
        return self.can_pass_objects_at(pos)
    
    def can_see_thru(self, pos: tuple[int, int]) -> bool:
        tile = self.get_tile_lower(pos)
        if not tile:
            return False
        if not tile.can_see_thru:
            return False
        return self.can_see_thru_objects_at(pos)
    
    def get_objects_at(self, pos: tuple[int, int], subtype: Node = Node) -> List[Node]:
        return [obj for obj in self.objects if obj.position == pos  and obj.__is__(subtype)]
    
    def get_objects_subset(self, subtype_wanted: Node = MapObject, obj_list: List[Node] = []):
        if not obj_list:
            obj_list = self.objects
        return [obj for obj in obj_list if obj.__is__(subtype_wanted)]
    
    def get_object_by_name(self, name: str) -> Node:
        for obj in self.objects:
            if obj.name == name:
                return obj
    
    def can_pass_objects_at(self, pos: tuple[int, int]) -> bool:
        objs = self.get_objects_at(pos)
        for obj in objs:
            if not obj.is_passable:
                return False
        return True
    
    def can_see_thru_objects_at(self, pos: tuple[int, int]) -> bool:
        objs = self.get_objects_at(pos)
        for obj in objs:
            if not obj.can_see_thru:
                return False
        return True
    
    def add_object(self, map_object: Node):
        self.objects.append(map_object)
        if map_object.layer not in self.objects_by_layer:
            self.objects_by_layer[map_object.layer] = []
        self.objects_by_layer[map_object.layer].append(map_object)
        if map_object.group_name:
            if map_object.group_name not in self.groups:
                self.groups[map_object.group_name] = NodeGroup(map_object)
            else:
                self.groups[map_object.group_name].add(map_object)
            map_object.group = self.groups[map_object.group_name]
            
        map_object.map = self
    
    def remove_object(self, map_object: Node):
        if map_object in self.objects:
            self.objects.remove(map_object)
            self.objects_by_layer[map_object.layer].remove(map_object)
    
    @classmethod
    def load_from_files(cls, map_name: str, map_obj_db: MapObjectDatabase, tile_db: TileDatabase, engine: 'GameEngine', objects_data: dict = None):
        """Load map from ASCII file and JSON mapping file"""
        print(map_name)
        map_folder = os.path.join(MAPS_DIR, map_name)
        map_file = os.path.join(map_folder, f"map_{map_name}.txt")
        mapping_file = os.path.join(map_folder, f"tiles_{map_name}.json")
        objects_file = os.path.join(map_folder, f"objs_{map_name}.json")
        levels_file = os.path.join(map_folder, f"levels_{map_name}.txt")
        
        if not os.path.exists(map_file):
            raise FileNotFoundError(f"Map file not found: {map_file}")
        
        if not os.path.exists(mapping_file):
            raise FileNotFoundError(f"Mapping file not found: {mapping_file}")
        
        # Load ASCII map
        with open(map_file, 'r', encoding='utf-8') as f:
            lines = [line.rstrip() for line in f.readlines()]
        
        if not lines:
            raise ValueError(f"Empty map file: {map_file}")
        
        # Load character to tile name mapping
        with open(mapping_file, 'r', encoding='utf-8') as f:
            char_to_tile = json.load(f)
        tile_levels = []
        if os.path.exists(levels_file):
            with open(levels_file, 'r', encoding='utf-8') as f:
                tile_levels = [line.rstrip() for line in f.readlines()]
            
            
        height = len(lines)
        width = max(len(line) for line in lines) if lines else 0
        game_map = cls(width, height, engine, map_name)
        # Parse tiles using the mapping
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                pos = (x, y)
                if char in char_to_tile:
                    tile_name = char_to_tile[char]
                    game_map.set_tile_by_name(pos, tile_name, tile_db, True)
                    game_map.tiles[y][x].level = 1 if not tile_levels else int(tile_levels[y][x])
                else:
                    # Default to grass if character not found in mapping
                    game_map.set_tile_by_name(pos, "grass", tile_db, True)

        # Load objects if file exists
        if os.path.exists(objects_file):
            with open(objects_file, 'r') as f:
                if not objects_data:
                    objects_data = json.load(f)
            for obj_name, obj_data in objects_data.items():
                if obj_name == "adjacent_maps":
                    for dir, map in obj_data["args"].items():
                        game_map.adjacent_maps[dir] = map
                map_object = map_obj_db.create_obj(obj_name, obj_data["object_type"], obj_data)
                game_map.add_object(map_object)
        return game_map
    
    def in_map_range(self, pos: tuple[int, int]):
        return pos[0] in range(self.width) and pos[1] in range(self.height)
    
    def to_dict(self):
        return {obj.name : obj.to_dict() for obj in self.objects if not obj.__is__(Character)}