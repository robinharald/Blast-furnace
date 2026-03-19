"""
Bank interaction handler.

Handles:
- Opening the bank chest by clicking the calibrated position
- Detecting when the bank interface is open (via color checks)
- Depositing inventory (except coal bag)
- Withdrawing specific items by finding them via color/search
- Stamina potion management
- Closing the bank
"""

import time
from config import ScreenRegions, Colors, COLOR_TOLERANCE, BotSettings
from screen.capture import (
    capture_screen, color_matches, get_pixel_color,
    region_has_color, capture_region, get_pixel_color_from_frame,
    find_color_in_region,
)
from game.inventory import InventoryReader
from game.coal_bag import CoalBagManager
from input import mouse
from anti_detect.humanizer import Humanizer
from data.bars import BarType, COAL_COLOR


class BankHandler:
    """
    All bank-related interactions.
    """

    def __init__(self, regions: ScreenRegions, settings: BotSettings,
                 inventory: InventoryReader, coal_bag: CoalBagManager,
                 humanizer: Humanizer):
        self.regions = regions
        self.settings = settings
        self.inventory = inventory
        self.coal_bag = coal_bag
        self.humanizer = humanizer

        # Trip counter for coal-loading cycles
        self._coal_trip = 0

    def is_bank_open(self):
        """
        Detect if the bank interface is open by checking for the
        characteristic bank background color in the expected region.
        """
        # Check multiple points in the bank title/header area
        # The bank interface has a distinctive brown background and orange title
        bx, by = self.regions.bank_pos
        # Sample a few pixels around the bank area for the interface background
        frame = capture_region(
            self.regions.game_x, self.regions.game_y,
            self.regions.game_w, self.regions.game_h
        )
        offset = (self.regions.game_x, self.regions.game_y)

        # Bank interface typically covers center of game viewport
        mid_x = self.regions.game_x + self.regions.game_w // 2
        mid_y = self.regions.game_y + 50  # Near top where title bar is

        color = get_pixel_color_from_frame(frame, mid_x, mid_y, offset)
        return color_matches(color, Colors.BANK_BG, COLOR_TOLERANCE) or \
               color_matches(color, Colors.BANK_TITLE, COLOR_TOLERANCE)

    def open_bank(self):
        """
        Click the bank chest to open the bank.
        Returns True if bank opened successfully.
        """
        if self.is_bank_open():
            return True

        bx, by = self.regions.bank_pos
        mouse.click(bx, by, variance=4)
        self.humanizer.reaction_delay()

        # Wait for bank to open (up to 3 seconds)
        for _ in range(15):
            if self.is_bank_open():
                self.humanizer.bank_delay()
                return True
            time.sleep(0.2)

        return False

    def close_bank(self):
        """Close the bank interface by pressing Escape."""
        if not self.is_bank_open():
            return True

        import pyautogui
        pyautogui.press("escape")
        self.humanizer.action_delay()

        for _ in range(10):
            if not self.is_bank_open():
                return True
            time.sleep(0.15)

        return not self.is_bank_open()

    def deposit_all_except_coal_bag(self):
        """
        Deposit entire inventory except the coal bag.
        Uses the "Deposit inventory" button, then withdraws coal bag back
        if it was deposited — OR clicks each item individually skipping
        the coal bag slot.

        Strategy: Click deposit-all button, then immediately withdraw coal bag.
        This is faster and more reliable than clicking individual slots.
        """
        if not self.is_bank_open():
            return False

        if self.settings.use_coal_bag:
            # Click the deposit inventory button
            dx, dy = self.regions.bank_deposit_inv_btn
            mouse.click(dx, dy, variance=3)
            self.humanizer.action_delay()
            self.humanizer.action_delay()

            # The coal bag got deposited too — withdraw it back
            # We need to find and click it in the bank
            # For reliability, we search for it by its known appearance
            self._withdraw_coal_bag()
        else:
            # No coal bag — just deposit all
            dx, dy = self.regions.bank_deposit_inv_btn
            mouse.click(dx, dy, variance=3)
            self.humanizer.action_delay()

        return True

    def _withdraw_coal_bag(self):
        """
        Withdraw the coal bag from bank back to inventory.
        Searches the bank for the coal bag appearance.
        """
        # Coal bag has a very distinct dark appearance
        # We click it in the bank to withdraw 1
        # For robustness, use the bank search feature
        self._bank_search("Coal bag")
        self.humanizer.bank_delay()
        # Click the first item in search results (top-left bank slot area)
        self._click_first_bank_slot()
        self.humanizer.action_delay()

        # Verify it's back in inventory
        time.sleep(0.3)
        return self.coal_bag.is_bag_present()

    def _bank_search(self, term):
        """
        Type a search term into the bank search box.
        Assumes bank is open. Clicks the search icon first.
        """
        import pyautogui

        # Click search button (magnifying glass at bottom of bank)
        sx, sy, sw, sh = self.regions.bank_search_region
        mouse.click(sx + sw // 2, sy + sh // 2, variance=2)
        self.humanizer.action_delay()

        # Type the search term
        pyautogui.typewrite(term, interval=0.05 + 0.03 * self.humanizer._base_speed)
        self.humanizer.bank_delay()

    def _click_first_bank_slot(self):
        """Click the first visible bank slot (for search results)."""
        # First bank slot is typically at a fixed position relative to bank window
        # This is roughly center-left of the bank grid
        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115
        mouse.click(bx, by, variance=3)

    def withdraw_ore(self, bar_type: BarType):
        """
        Withdraw the correct ores for the current bar type and trip cycle.
        Handles coal-requiring bars with trip counting.

        Returns True if items were withdrawn successfully.
        """
        if not self.is_bank_open():
            return False

        data = bar_type.data

        if data.requires_coal:
            return self._withdraw_coal_bar_cycle(bar_type)
        elif data.ore.has_two_ores:
            return self._withdraw_two_ores(bar_type)
        else:
            return self._withdraw_simple_ore(bar_type)

    def _withdraw_simple_ore(self, bar_type: BarType):
        """Withdraw a full inventory of a single ore type (iron, silver, gold)."""
        ore_name = bar_type.data.ore.primary_ore
        self._bank_search(ore_name)
        self.humanizer.bank_delay()

        # Right-click first bank slot -> "Withdraw-All"
        self._withdraw_all_from_first_slot()
        self.humanizer.action_delay()
        return True

    def _withdraw_two_ores(self, bar_type: BarType):
        """Withdraw two ore types (bronze: copper + tin)."""
        # Withdraw 14 of primary
        self._bank_search(bar_type.data.ore.primary_ore)
        self.humanizer.bank_delay()
        self._withdraw_x_from_first_slot(14)
        self.humanizer.action_delay()

        # Withdraw 14 of secondary
        self._bank_search(bar_type.data.ore.secondary_ore)
        self.humanizer.bank_delay()
        self._withdraw_x_from_first_slot(14)
        self.humanizer.action_delay()
        return True

    def _withdraw_coal_bar_cycle(self, bar_type: BarType):
        """
        Handle the coal trip cycle for steel/mithril/adamant/rune.

        Trip pattern with coal bag:
        - Coal trips: fill coal bag + withdraw 27 coal in inventory
        - Ore trip: fill coal bag + withdraw 27 ore in inventory

        Steel (1 coal): every trip is ore + coal bag
        Mithril (2 coal): 1 coal trip, then 1 ore trip
        Adamantite (3 coal): 2 coal trips, then 1 ore trip
        Runite (4 coal): 3 coal trips, then 1 ore trip
        """
        coal_per_bar = bar_type.data.coal_per_bar

        if self.settings.use_coal_bag:
            # Always fill coal bag first
            self.coal_bag.fill()
            self.humanizer.action_delay()

            if self._coal_trip < coal_per_bar - 1:
                # Coal-loading trip: fill inventory with coal
                self._bank_search("Coal")
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip += 1
                self.humanizer.action_delay()
                return True
            else:
                # Ore trip: fill inventory with primary ore
                self._bank_search(bar_type.data.ore.primary_ore)
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip = 0
                self.humanizer.action_delay()
                return True
        else:
            # No coal bag: alternate between full coal and full ore
            if self._coal_trip < coal_per_bar:
                self._bank_search("Coal")
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip += 1
            else:
                self._bank_search(bar_type.data.ore.primary_ore)
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip = 0
            self.humanizer.action_delay()
            return True

    def is_ore_trip(self, bar_type: BarType):
        """Check if the current trip deposits ore (triggers bar smelting)."""
        if not bar_type.data.requires_coal:
            return True
        coal_per_bar = bar_type.data.coal_per_bar
        if self.settings.use_coal_bag:
            # Ore trip happens when coal_trip counter was at max and just reset
            return self._coal_trip == 0
        else:
            return self._coal_trip == 0

    def handle_stamina(self):
        """
        Check run energy and drink a stamina potion if needed.
        Withdraws from bank if necessary.
        """
        if not self.settings.use_stamina:
            return

        # Check run energy via the minimap orb color
        # If stamina effect is active (orange orb), skip
        from screen.capture import get_pixel_color
        orb_color = get_pixel_color(self.regions.minimap_cx + 30,
                                     self.regions.minimap_cy + 70)

        if color_matches(orb_color, Colors.STAMINA_ACTIVE, 30):
            return  # Already have stamina effect

        if color_matches(orb_color, Colors.RUN_ORB_ACTIVE, 30):
            return  # Run energy seems fine

        # Need stamina — search for it in bank
        if self.is_bank_open():
            self._bank_search("Stamina")
            self.humanizer.bank_delay()
            self._withdraw_x_from_first_slot(1)
            self.humanizer.action_delay()

            # Close bank to drink
            self.close_bank()
            self.humanizer.action_delay()

            # Find and click the stamina potion in inventory
            # Stamina potions have a yellow/orange color
            stam_color = (200, 160, 40)
            stam_slot = self.inventory.find_first_slot_with_color(
                stam_color, tolerance=35,
                exclude_slot=self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None
            )
            if stam_slot is not None:
                self.inventory.click_slot(stam_slot)
                self.humanizer.action_delay()

            # Re-open bank
            self.open_bank()
            self.humanizer.bank_delay()

            # Deposit empty vial if present
            vial_color = (180, 180, 200)  # Empty vial is light colored
            vial_slot = self.inventory.find_first_slot_with_color(
                vial_color, tolerance=30,
                exclude_slot=self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None
            )
            if vial_slot is not None:
                self.inventory.click_slot(vial_slot)
                self.humanizer.action_delay()

    def has_supplies(self, bar_type: BarType):
        """
        Quick check if the bank likely has the ores needed.
        Done by searching and checking if any results appear.
        """
        if not self.is_bank_open():
            return False

        self._bank_search(bar_type.data.ore.primary_ore)
        self.humanizer.bank_delay()

        # Check if first bank slot has an item
        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115
        color = get_pixel_color(bx, by)
        has_ore = not color_matches(color, Colors.BANK_SLOT_EMPTY, COLOR_TOLERANCE)

        if bar_type.data.requires_coal and has_ore:
            self._bank_search("Coal")
            self.humanizer.bank_delay()
            color = get_pixel_color(bx, by)
            has_coal = not color_matches(color, Colors.BANK_SLOT_EMPTY, COLOR_TOLERANCE)
            return has_ore and has_coal

        return has_ore

    def reset_trip_counter(self):
        """Reset the coal trip counter."""
        self._coal_trip = 0

    def get_coal_trip(self):
        """Get current coal trip counter."""
        return self._coal_trip

    def _withdraw_all_from_first_slot(self):
        """Right-click first bank slot and select 'Withdraw-All'."""
        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115

        mouse.right_click(bx, by, variance=2)
        self.humanizer.action_delay()

        # "Withdraw-All" is typically the 5th option in right-click menu
        # Each menu option is ~15px apart
        mouse.click(bx, by + 75, variance=2)
        self.humanizer.action_delay()

    def _withdraw_x_from_first_slot(self, amount):
        """Right-click and withdraw a specific amount."""
        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115

        if amount == 1:
            # Left-click withdraws 1
            mouse.click(bx, by, variance=2)
        else:
            mouse.right_click(bx, by, variance=2)
            self.humanizer.action_delay()
            # Select "Withdraw-X" then type amount
            # Withdraw-X is typically the 6th option
            mouse.click(bx, by + 90, variance=2)
            self.humanizer.action_delay()
            import pyautogui
            pyautogui.typewrite(str(amount), interval=0.05)
            pyautogui.press("enter")
            self.humanizer.action_delay()
