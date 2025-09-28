from typing import List, Dict, Any, Optional, TYPE_CHECKING
from tiles.tiles import Tile
from tiles.tile_templates import Floor
if TYPE_CHECKING:
    from ultimalike import GameEngine
class TileDatabase:
    def __init__(self, engine: 'GameEngine'):
        self.tiles: Dict[str, Tile] = {}
        self.engine = engine
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
        tile = self.tiles.get(name)
        if tile:
            return tile()
        return None
    
    def add_tile(self, name: str, tile: Tile):
        """Add a new tile to the database"""
        self.tiles[name] = tile