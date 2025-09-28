from typing import TYPE_CHECKING
from constants import GameState
import pygame
if TYPE_CHECKING:
    from ultimalike import GameEngine
def shop_inputs(self: 'GameEngine', event):
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
        case pygame.K_ESCAPE:
            self.revert_state()
    if items:
        self.merchant.selected_item = items[self.merchant.scroll_index]