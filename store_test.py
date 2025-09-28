import pygame
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, List, OrderedDict
from constants import EquipmentSlot, EffectType, EffectTrigger, SCREEN_HEIGHT, SCREEN_WIDTH, GOLD, LIGHT_GRAY, PURPLE, DARK_GRAY, GREEN, RED, GRAY, GAME_TITLE, BLACK, WHITE, BLUE, GRAY, TILE_WIDTH, TILE_HEIGHT
from enum import Enum
from objects.characters import Character, Party
import json
from items.itemz import ItemDatabase, Item

# Required enums and classes based on your code structure
#width = 1200 height = 800
class Renderer:
    def __init__(self, engine: 'GameEngine'):
        self.engine = engine
        self.screen = self.engine.screen
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.SysFont("consolas", 15)
        self.large_font = pygame.font.SysFont("consolas", 30)
        self.side_font = pygame.font.SysFont("consolas", 20)
        self.max_cache_size: int = 250
        self.text_cache: OrderedDict[tuple[str, pygame.font.Font, tuple[int, int, int]], pygame.Surface] = OrderedDict()
        self.rect_cache: OrderedDict[(tuple[pygame.Surface, pygame.font.Font, tuple[int, int, int, int], tuple[int, int, int], tuple[int, int, int]]), pygame.Rect] = OrderedDict()
    def get_cached_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, font, color)
        if key not in self.text_cache:
            self.text_cache[key] = font.render(text, True, color)
        else:
            self.text_cache.move_to_end(key)
        if len(self.text_cache) > self.max_cache_size:
            self.text_cache.popitem(last = False)
        return self.text_cache[key]
    def draw_text_with_outline(self, text: str, font: pygame.font.Font, pos: tuple[int, int], text_color: tuple[int, int, int], outline_color=BLACK):
        """Draw text with a black outline for better visibility."""
        base = self.get_cached_text(text, font, text_color)
        outline = self.get_cached_text(text, font, outline_color)
        # Draw outline by rendering text offset in each direction
        if text_color != BLACK:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        self.screen.blit(outline, (pos[0] + dx, pos[1] + dy))
        # Draw actual text on top
        self.screen.blit(base, pos)
        return base.get_width(), base.get_height()

    def get_rectangle(self, w0_factor: int = 1, h0_factor: int = 1, w1_factor: int = 1, h1_factor: int = 1, color_rect0: tuple[int, int, int] = WHITE, color_rect1: tuple[int, int, int] = BLACK):
        rect = pygame.Rect(SCREEN_WIDTH // w0_factor, SCREEN_HEIGHT // h0_factor, SCREEN_WIDTH // w1_factor, SCREEN_HEIGHT // h1_factor)
        pygame.draw.rect(self.screen, color_rect0, rect)
        pygame.draw.rect(self.screen, color_rect1, rect, 2)
        return rect
    
    def draw_background(self):
        """Draw the store background"""
        self.screen.fill(DARK_GRAY)
        
        # Draw store title
        title = self.get_cached_text("Merchant's Store", self.large_font, GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT//25))
        self.screen.blit(title, title_rect)
        
        # Draw gold display
        self.draw_text_with_outline(f"Gold: {self.engine.party.gold}", self.small_font, (20, 20), GOLD)
    def draw_mode_buttons(self):
        """Draw buy/sell mode buttons"""
        buy_color = GREEN if self.engine.merchant.mode == "buy" else GRAY
        sell_color = RED if self.engine.merchant.mode == "sell" else GRAY
        
        # Buy button
        buy_text = self.get_cached_text("BUY", self.side_font, BLACK)
        buy_rect = pygame.Rect(SCREEN_WIDTH // 24, SCREEN_HEIGHT // 10, SCREEN_WIDTH // 12, SCREEN_HEIGHT // 20)
        pygame.draw.rect(self.screen, buy_color, buy_rect)
        pygame.draw.rect(self.screen, BLACK, buy_rect, 2)
        buy_text_rect = buy_text.get_rect(center=buy_rect.center)
        self.screen.blit(buy_text, buy_text_rect)
        
        # Sell button
        
        sell_text = self.get_cached_text("SELL", self.side_font, BLACK)
        sell_rect = pygame.Rect(SCREEN_WIDTH // 7, SCREEN_HEIGHT // 10, SCREEN_WIDTH // 12, SCREEN_HEIGHT // 20)
        pygame.draw.rect(self.screen, sell_color, sell_rect)
        pygame.draw.rect(self.screen, BLACK, sell_rect, 2)
        sell_text_rect = sell_text.get_rect(center=sell_rect.center)
        self.screen.blit(sell_text, sell_text_rect)
        
        return buy_rect, sell_rect
    
    def draw_category_buttons(self):
        """Draw category filter buttons"""
        button_width = self.get_cached_text(self.engine.merchant.longest_category, self.small_font, LIGHT_GRAY).get_width() + SCREEN_WIDTH // 80
        button_height = SCREEN_HEIGHT // 20
        start_x = SCREEN_WIDTH // 24
        start_y = SCREEN_HEIGHT // 6
        
        category_rects = []
        
        for i, cat in enumerate(self.engine.merchant.categories):#Unroll these later
            x = start_x + (i * (button_width + 5))
            if x + button_width > 3*SCREEN_WIDTH // 4:  # Leave space for party view
                break
                
            rect = pygame.Rect(x, start_y, button_width, button_height)
            color = BLUE if self.engine.merchant.category == cat else LIGHT_GRAY
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 1)
            
            text_color = WHITE if self.engine.merchant.category == cat else BLACK
            cat_text = self.get_cached_text(cat.upper(), self.small_font, text_color)
            text_rect = cat_text.get_rect(center=rect.center)
            self.screen.blit(cat_text, text_rect)
            
            category_rects.append((rect, cat))
        
        return category_rects
    
    def draw_party_selection(self):
        
        party_rect = pygame.Rect(8*SCREEN_WIDTH//11, SCREEN_HEIGHT // 80, 23*SCREEN_WIDTH//88, 39*SCREEN_HEIGHT // 40)
        pygame.draw.rect(self.screen, WHITE, party_rect)
        pygame.draw.rect(self.screen, BLACK, party_rect, 2)
        
        # Title
        title_text = self.get_cached_text("Party Members", self.side_font, BLACK)
        self.screen.blit(title_text, (party_rect.x + (party_rect.width - title_text.get_width())//2, party_rect.y + SCREEN_HEIGHT//108))
        
        member_rects = []
        
        # Draw 2 members per row
        for i, member in enumerate(self.engine.party.members):
            row = i // 2
            col = i % 2
            
            x = party_rect.x + party_rect.width/32 + + col * (2*TILE_WIDTH + SCREEN_WIDTH // 13)
            y = party_rect.y + title_text.get_height() + SCREEN_HEIGHT//108 + row * (2*TILE_HEIGHT + SCREEN_HEIGHT // 7 + 7)
            
            member_rect = pygame.Rect(x, y, 2*TILE_WIDTH + SCREEN_WIDTH // 16, 2*TILE_HEIGHT + SCREEN_HEIGHT // 7)
            
            pygame.draw.rect(self.screen, LIGHT_GRAY, member_rect)
            pygame.draw.rect(self.screen, BLACK, member_rect, 1)
            
            # Member name
            name_text = self.get_cached_text(member.name, self.small_font, BLACK)
            name_rect = name_text.get_rect(center=(member_rect.centerx, member_rect.y + 10))
            self.screen.blit(name_text, name_rect)
            
            # Current equipment in slot
            selected_item = self.engine.merchant.selected_item
            slot_key = selected_item.slot.value if selected_item.slot else None
            current_item = member.equipped.get(slot_key) if slot_key else None
            def compare_stats_for_equipment(current_stat, new_stat, text_shorthand, y_offset):
                text_width, _ = self.draw_text_with_outline(f"{text_shorthand}:{current_stat}", self.small_font, (member_rect.x + 2, member_rect.bottom - y_offset), BLACK)
                if current_stat == new_stat:
                    return
                compare_color = RED if new_stat < current_stat else GREEN
                self.draw_text_with_outline(f"-> {new_stat} ({new_stat-current_stat})", self.small_font, (member_rect.x + 2 + text_width, member_rect.bottom - y_offset), compare_color)
                
            
            # Current stats
            current_max_hp = member.get_max_hp()
            current_power = member.get_total_power()
            current_guard = member.get_total_guard()
            
            # Calculate new stats if item were equipped
            new_max_hp = current_max_hp - (current_item.max_hp if current_item else 0) + selected_item.max_hp
            new_power = current_power - (current_item.power if current_item else 0) + selected_item.power
            new_guard = current_guard - (current_item.guard if current_item else 0) + selected_item.guard
            compare_stats_for_equipment(current_max_hp, new_max_hp, "HP", 45)
            compare_stats_for_equipment(current_power, new_power, "POW", 30)
            compare_stats_for_equipment(current_guard, new_guard, "GRD", 15)

            member_rects.append((member_rect, i))
        
        return member_rects
    
    def draw_item_list(self):
        """Draw the list of items"""
        items = self.engine.merchant.get_filtered_items()
        
        # Calculate visible items based on scroll
        start_index = self.engine.merchant.start_index
        end_index = min(start_index + self.engine.merchant.items_per_page, len(self.engine.merchant.store_items))
        
        y_start = 9*SCREEN_HEIGHT//40
        item_rects = []
        
        for i, item in enumerate(items[start_index:end_index]):
            y_pos = y_start + i * self.engine.merchant.item_height
            
            # Adjust width based on whether party view is showing
            list_width = 3*SCREEN_WIDTH//12
            
            # Item background
            item_rect = pygame.Rect(SCREEN_WIDTH//24, y_pos, list_width, self.engine.merchant.item_height - SCREEN_HEIGHT//160)
            color = LIGHT_GRAY if item == self.engine.merchant.selected_item else WHITE
            pygame.draw.rect(self.screen, color, item_rect)
            pygame.draw.rect(self.screen, BLACK, item_rect, 2)
            
            # Item info
            name_text = self.get_cached_text(item.name, self.side_font, BLACK)
            name_rect = name_text.get_rect(left=item_rect.x+SCREEN_WIDTH//120, centery=item_rect.centery)
            self.draw_text_with_outline(item.name, self.side_font, (name_rect.x, name_rect.y), BLACK)
            #Quantity Info
            qty_text = self.get_cached_text(f"x{item.quantity}", self.side_font, BLUE)
            qty_rect = qty_text.get_rect(left = item_rect.x + SCREEN_WIDTH//120 + name_rect.width + 7, centery=item_rect.centery)
            self.draw_text_with_outline(f"x{item.quantity}", self.side_font, (qty_rect.x, qty_rect.y), BLUE)
            
            # Price and quantity
            price_text = self.get_cached_text(f"${item.value}", self.side_font, GOLD)
            price_rect = price_text.get_rect(right=item_rect.right - SCREEN_WIDTH//120, centery=item_rect.centery)
            self.draw_text_with_outline(f"${item.value}", self.side_font, (price_rect.x, price_rect.y), GOLD)
            
            item_rects.append((item_rect, item))
        
        return item_rects
    
    def draw_action_buttons(self):
        """Draw buy/sell action buttons"""
        if not self.engine.merchant.selected_item:
            return []
        
        button_y = SCREEN_HEIGHT - 80
        
        if self.engine.merchant.mode == "buy":
            # Check if player can afford
            can_afford = self.engine.party.gold >= self.engine.merchant.selected_item.value
            buy_color = GREEN if can_afford else GRAY
            
            buy_rect = pygame.Rect(50, button_y, 300, 40)
            pygame.draw.rect(self.screen, buy_color, buy_rect)
            pygame.draw.rect(self.screen, BLACK, buy_rect, 2)
            
            buy_text = self.get_cached_text("Press Enter to Buy Item", self.side_font, BLACK)
            buy_text_rect = buy_text.get_rect(center=buy_rect.center)
            self.screen.blit(buy_text, buy_text_rect)
            
            return [buy_rect] if can_afford else []
        
        else:  # sell mode
            if not self.engine.merchant.selected_item.can_be_sold:
                return []
            
            sell_rect = pygame.Rect(50, button_y, 120, 40)
            pygame.draw.rect(self.screen, RED, sell_rect)
            pygame.draw.rect(self.screen, BLACK, sell_rect, 2)
            
            sell_text = self.get_cached_text("SELL ITEM", self.side_font, BLACK)
            sell_text_rect = sell_text.get_rect(center=sell_rect.center)
            self.screen.blit(sell_text, sell_text_rect)
            
            return [sell_rect]

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
        self.engine.party.add_item_by_id(self.selected_item.name, 1)
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

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.FPS = 60
        self.item_db = ItemDatabase()
        self.merchant = MerchantStore(self)
        self.party = Party(self)
        self.gold: int = 500
        
        # Create 8 party members with sample equipment
        member_names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Henry"]
        for i, name in enumerate(member_names):
            char = Character(
                name=name,
                x=0,
                y=0,
                args={},
                level=1 + i,
                hp=100 + i * 10,
                max_hp=100 + i * 10,
                strength=10 + i * 2,
                dexterity=10 + i,
                faith=10 + i
            )
            # Give some members basic equipment
            if i < 4:
                char.equipped[EquipmentSlot.WEAPON.value] = Item(
                    name=f"Basic Sword {i+1}", description="A simple blade", uid=2000+i,
                    power=5+i*2, item_type="equipment", slot=EquipmentSlot.WEAPON
                )
            self.party.members.append(char)
        self.renderer = Renderer(self)
        self.running = True
    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    items = self.merchant.get_filtered_items()
                    match event.key:
                        case pygame.K_UP | pygame.K_DOWN:
                            
                            if event.key == pygame.K_UP:  # Scroll up
                                if self.merchant.scroll_index > 0:
                                    self.merchant.scroll_index -= 1
                                    if self.merchant.scroll_index < self.merchant.start_index:
                                        self.merchant.start_index -= 1 
                            elif event.key == pygame.K_DOWN:  # Scroll down
                                if self.merchant.scroll_index < len(items) - 1:
                                    self.merchant.scroll_index += 1
                                    if self.merchant.scroll_index >= self.merchant.start_index + self.merchant.items_per_page:
                                        self.merchant.start_index += 1 
                            
                        case pygame.K_LEFT | pygame.K_RIGHT:
                            for i, cat in enumerate(self.merchant.categories):
                                if cat == self.merchant.category:
                                    if event.key == pygame.K_LEFT:
                                        if i > 0:
                                            self.selected_item = None
                                            items = self.merchant.get_filtered_items()
                                            self.scroll_index = 0
                                            self.merchant.category = self.merchant.categories[i-1]
                                        break
                                    if event.key == pygame.K_RIGHT:
                                        if i < len(self.merchant.categories)-1:
                                            self.selected_item = None
                                            items = self.merchant.get_filtered_items()
                                            self.scroll_index = 0
                                            self.merchant.category = self.merchant.categories[i+1]
                                        break
                            self.selected_item = None
                            items = self.merchant.get_filtered_items()
                            self.scroll_index = 0
                        case pygame.K_TAB:
                            self.merchant.mode = "sell" if self.merchant.mode == "buy" else "buy"
                            self.selected_item = None
                            items = self.merchant.get_filtered_items()
                            self.scroll_index = 0
                        case pygame.K_RETURN:
                            if self.merchant.mode == "buy":
                                self.merchant.handle_buy_item()
                            else:
                                self.merchant.handle_sell_item()
                    if items:
                        self.merchant.selected_item = items[self.merchant.scroll_index]
                

            
            # Draw everything
            self.renderer.draw_background()
            self.renderer.draw_mode_buttons()
            self.renderer.draw_category_buttons()
            self.renderer.draw_party_selection()
            self.renderer.draw_item_list()
            self.renderer.draw_action_buttons()
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    store = GameEngine()
    store.run()