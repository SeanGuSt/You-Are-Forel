from typing import List, Dict, Any, Optional
from tiles.tiles import Tile
from tiles.tile_templates import Floor
class TileDatabase:
    def __init__(self):
        self.tiles: Dict[str, Tile] = {}
        def get_all_subclasses(subclass):
            subclasses = subclass.__subclasses__()
            for subclass in subclasses:
                subclasses += get_all_subclasses(subclass)
            return subclasses
        obj_classes = get_all_subclasses(Tile)
        for cls in obj_classes:
            self.tiles[cls.__name__.lower()] = cls
    
    def get_tile(self, name: str) -> Optional[Tile]:
        """Get a tile by name"""
        return self.tiles.get(name)
    
    def add_tile(self, name: str, tile: Tile):
        """Add a new tile to the database"""
        self.tiles[name] = tile