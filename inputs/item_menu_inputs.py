from typing import TYPE_CHECKING
import pygame
from constants import GameState, EquipmentSlot

if TYPE_CHECKING:
    from ultimalike import GameEngine

def equipment_menu_inputs(self: 'GameEngine', event):
    match event.key:
        case pygame.K_ESCAPE:
            self.revert_state()
            self.show_equipment_list = False
        case pygame.K_i:
            self.replace_state(GameState.MENU_INVENTORY)
            self.show_equipment_list = False
        case pygame.K_UP:
            if self.show_equipment_list:
                current_slot = list(EquipmentSlot)[self.selected_slot]
                available_equipment = [eq for eq in self.party.inventory 
                                    if eq.slot == current_slot]
                if available_equipment:
                    self.selected_equipment = max(0, self.selected_equipment - 1)
            else:
                self.selected_slot = max(0, self.selected_slot - 1)
        case pygame.K_DOWN:
            if self.show_equipment_list:
                current_slot = list(EquipmentSlot)[self.selected_slot]
                available_equipment = [eq for eq in self.party.inventory 
                                    if eq.slot == current_slot]
                if available_equipment:
                    self.selected_equipment = min(len(available_equipment) - 1, 
                                                self.selected_equipment + 1)
            else:
                self.selected_slot = min(len(EquipmentSlot) - 1, self.selected_slot + 1)
        case pygame.K_BACKSPACE:
            if self.show_equipment_list:
                self.show_equipment_list = False
        case pygame.K_RETURN:
            if self.show_equipment_list:
                equip_selected_item(self)
            else:
                current_slot = list(EquipmentSlot)[self.selected_slot]
                available_equipment = [eq for eq in self.party.inventory 
                                    if eq.slot == current_slot]
                if available_equipment:
                    self.show_equipment_list = True
                    self.selected_equipment = 0
        case pygame.K_u:  # Unequip
            if not self.show_equipment_list:
                unequip_selected_item(self)
    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, 
                    pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8]:
        member_index = event.key - pygame.K_1
        if member_index < len(self.party.members):
            self.selected_member = member_index
            self.show_equipment_list = False

def inventory_menu_inputs(self: 'GameEngine', event):
    inventory = self.party.inventory
    match event.key:
        case pygame.K_ESCAPE:
            if not self.picking_item_to_show:
                self.revert_state()
                self.show_equipment_list = False
        case pygame.K_e:
            if not self.picking_item_to_show:
                self.replace_state(GameState.MENU_EQUIPMENT)
                self.show_equipment_list = True
        case pygame.K_UP:
            self.selected_equipment = (self.selected_equipment - 1) % len(inventory)
        case pygame.K_DOWN:
            self.selected_equipment = (self.selected_equipment + 1) % len(inventory)
        case pygame.K_RETURN:
            if self.picking_item_to_show:
                self.revert_state()
                self.picking_item_to_show = False
                self.dialog_manager.user_input = "show " + inventory[self.selected_equipment].name

def stats_menu_inputs(self: 'GameEngine', event):
    if event.key == pygame.K_ESCAPE:
        self.revert_state()

def equip_selected_item(self: 'GameEngine'):
    """Equip the selected equipment item"""
    if not self.party.members:
        return
        
    current_member = self.party.members[self.selected_member]
    current_slot = list(EquipmentSlot)[self.selected_slot]
    available_equipment = [eq for eq in self.party.inventory if eq.slot == current_slot]
    
    if available_equipment and self.selected_equipment < len(available_equipment):
        equipment_to_equip = available_equipment[self.selected_equipment]
        
        # Remove from inventory
        self.party.remove_item(equipment_to_equip)
        
        # Equip the item (this returns previously equipped item if any)
        previously_equipped = current_member.equip_item(equipment_to_equip)
        
        # Add previously equipped item back to inventory
        if previously_equipped:
            self.party.add_item(previously_equipped)
        
        self.append_to_message_log(f"{current_member.name} equipped {equipment_to_equip.name}")
        self.show_equipment_list = False

def unequip_selected_item(self: 'GameEngine'):
    """Unequip the item in the selected slot"""
    if not self.party.members:
        return
        
    current_member = self.party.members[self.selected_member]
    current_slot = list(EquipmentSlot)[self.selected_slot]
    
    unequipped_item = current_member.unequip_item(current_slot)
    
    if unequipped_item:
        self.party.add_item(unequipped_item)
        self.append_to_message_log(f"{current_member.name} unequipped {unequipped_item.name}")