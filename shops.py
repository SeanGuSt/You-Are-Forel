import pygame
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, List, OrderedDict, TYPE_CHECKING
from constants import EquipmentSlot, EffectType, EffectTrigger, SCREEN_HEIGHT, SCREEN_WIDTH, GOLD, LIGHT_GRAY, PURPLE, DARK_GRAY, GREEN, RED, GRAY, GAME_TITLE, BLACK, WHITE, BLUE, GRAY, TILE_WIDTH, TILE_HEIGHT
from enum import Enum
from objects.characters import Character, Party
import json
from items.itemz import ItemDatabase, Item

if TYPE_CHECKING:
    from ultimalike import GameEngine

class MerchantStore:
    def __init__(self, engine: 'GameEngine'):
        self.engine = engine
        
        # Store state
        self.mode = "buy"  # "buy" or "sell"
        # Categories for filtering
        self.categories = ["All", "Consumables", "Weapons", "Bows", "Armor", "Accessories"]
        self.longest_category = "All"
        for i in self.categories:
            if len(self.longest_category) < len(i):
                self.longest_category = i
        self.category = self.categories[0]  # Item category filter
        
        self.selected_character = 0  # Index of selected party member
        self.scroll_index = 0
        
        # UI elements
        self.item_height = SCREEN_HEIGHT // 15
        self.start_index = 0
        self.items_per_page = 7
        self.store_items = []
        # Add starting items
        with open("store_test_inventory.json", 'r') as f:
            starting_items = json.load(f)
            for name, quantity in starting_items.items():
                self.add_item_by_name(name, quantity)
        self.selected_item = self.store_items[0]
        

    def add_item(self, item: Item):
        # Check if item already exists
        if self.store_items and item:
            for existing_item in self.store_items:
                if existing_item.name == item.name:
                    existing_item.quantity += item.quantity
                    return
        self.store_items.append(item)
    
    def add_item_by_name(self, item_name: str, quantity: int = 1):
        self.add_item(self.engine.item_db.create_item(item_name, quantity))
    
    def get_filtered_items(self):
        """Get items filtered by current category and mode"""
        items = self.store_items if self.mode == "buy" else self.engine.party.inventory
        
        if self.category == "All":
            return items
        
        # Map slot types to categories
        slot_mapping = {
            "Consumables" : None,
            "Weapons": EquipmentSlot.WEAPON,
            "Bows" : EquipmentSlot.RANGED,
            "Armor": EquipmentSlot.ARMOR,
            "Accessories": EquipmentSlot.ACCESSORY
        }
        
        if self.category in slot_mapping:
            return [item for item in items if item.slot == slot_mapping[self.category]]
        else:
            return [item for item in items if item.item_type == self.category]
    
    def handle_buy_item(self):
        """Handle buying an item"""
        if not self.selected_item or self.engine.party.gold < self.selected_item.value:
            return
        
        # Deduct gold
        self.engine.party.gold -= self.selected_item.value
        self.engine.party.add_item_by_id(self.selected_item.item_id, 1)
        # Reduce store quantity
        if self.selected_item.quantity > 1:
            self.selected_item.quantity -= 1
        else:
            self.store_items.remove(self.selected_item)
            self.selected_item = None
    
    def handle_sell_item(self):
        """Handle selling an item"""
        if not self.selected_item or not self.selected_item.can_be_sold:
            return
        
        # Add gold (typically at reduced price)
        sell_price = max(1, self.selected_item.value // 2)
        self.engine.party.gold += sell_price
        
        # Remove from party inventory
        if self.selected_item.quantity > 1:
            self.selected_item.quantity -= 1
        else:
            self.engine.party.inventory.remove(self.selected_item)
            self.selected_item = None