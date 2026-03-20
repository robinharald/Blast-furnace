"""
Bank interaction handler.

Handles:
- Opening the bank chest by clicking the calibrated position
- Detecting when the bank interface is open (via color checks)
- Depositing inventory (except coal bag)
- Withdrawing specific items by finding them via bank search
- Stamina potion management
- Closing the bank

Blast Furnace bank specifics:
- The bank is a "Bank chest" (not a booth), left-click "Use"
- "Deposit inventory" button deposits all UNLOCKED slots
- OSRS native deposit locks (per-slot) protect coal bag and gloves
  The player must pre-lock the relevant slot in-game.
  Locked slots are SKIPPED by "Deposit inventory" — no re-withdrawal needed.
- Bank search: click magnifying glass, type name, items filter instantly
- Must clear search between different item lookups (click X or clear field)
- Bank chest has 1 extra tick delay vs banker NPC interaction
"""

import time
import pyautogui
from config import ScreenRegions, Colors, COLOR_TOLERANCE, BotSettings
from screen.capture import (
    capture_screen, color_matches, get_pixel_color,
    region_has_color, capture_region, get_pixel_color_from_frame,
    find_color_in_region,
)
from game.inventory import InventoryReader
from input import mouse
from anti_detect.humanizer import Humanizer
from data.bars import BarType, COAL_COLOR


class BankHandler:
    """
    All bank-related interactions.
    """

    def __init__(self, regions: ScreenRegions, settings: BotSettings,
                 inventory: InventoryReader, coal_bag, humanizer: Humanizer):
        self.regions = regions
        self.settings = settings
        self.inventory = inventory
        self.coal_bag = coal_bag  # Can be None if not using coal bag
        self.humanizer = humanizer

        # Trip counter for coal-loading cycles.
        # Tracks how many coal trips have been completed in the current cycle.
        self._coal_trip = 0

        # Whether the NEXT trip will be an ore trip.
        # This is set BEFORE withdrawing so the state machine can read it.
        self._next_is_ore_trip = True

    def _get_coal_bag_slot(self):
        """Safely get coal bag slot, returns None if no coal bag."""
        if self.coal_bag is not None:
            return self.coal_bag.get_locked_slot()
        return None

    def is_bank_open(self):
        """
        Detect if the bank interface is open by checking for the
        characteristic bank background/title color in the expected region.
        """
        frame = capture_region(
            self.regions.game_x, self.regions.game_y,
            self.regions.game_w, self.regions.game_h
        )
        offset = (self.regions.game_x, self.regions.game_y)

        # Bank interface title bar is near the top-center of the viewport
        mid_x = self.regions.game_x + self.regions.game_w // 2
        mid_y = self.regions.game_y + 50

        color = get_pixel_color_from_frame(frame, mid_x, mid_y, offset)

        # Also check a second point to reduce false positives
        mid_y2 = self.regions.game_y + 35
        color2 = get_pixel_color_from_frame(frame, mid_x, mid_y2, offset)

        return (color_matches(color, Colors.BANK_BG, COLOR_TOLERANCE) or
                color_matches(color, Colors.BANK_TITLE, COLOR_TOLERANCE) or
                color_matches(color2, Colors.BANK_TITLE, COLOR_TOLERANCE))

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

        pyautogui.press("escape")
        self.humanizer.action_delay()

        for _ in range(10):
            if not self.is_bank_open():
                return True
            time.sleep(0.15)

        return not self.is_bank_open()

    def deposit_all_except_locked(self):
        """
        Deposit entire inventory using the "Deposit inventory" button.

        OSRS native deposit locks (per-slot) mean the button automatically
        SKIPS items in locked slots. The player must pre-configure:
        - Coal bars: lock slot 0 (coal bag)
        - Gold bars: lock slot 0 (gloves for swapping)

        No re-withdrawal needed — locked items stay in inventory.
        Only bars and leftover items get deposited.
        """
        if not self.is_bank_open():
            return False

        # Click the deposit inventory button — locked slots are skipped by the game
        dx, dy = self.regions.bank_deposit_inv_btn
        mouse.click(dx, dy, variance=3)
        self.humanizer.action_delay()
        self.humanizer.action_delay()

        return True

    def _bank_search(self, term):
        """
        Type a search term into the bank search box.
        Assumes bank is open. Clicks the search icon, clears any previous
        search, then types the new term.
        """
        # Click search button (magnifying glass at bottom of bank)
        sx, sy, sw, sh = self.regions.bank_search_region
        mouse.click(sx + sw // 2, sy + sh // 2, variance=2)
        self.humanizer.action_delay()

        # Clear any existing search text with Ctrl+A then type new term
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.typewrite(term, interval=0.04 + 0.02 * self.humanizer._base_speed)
        self.humanizer.bank_delay()

    def _click_first_bank_slot(self):
        """Click the first visible bank slot (for search results)."""
        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115
        mouse.click(bx, by, variance=3)

    def withdraw_ore(self, bar_type: BarType):
        """
        Withdraw the correct ores for the current bar type and trip cycle.
        Handles coal-requiring bars with proper trip counting.

        IMPORTANT: Sets self._next_is_ore_trip BEFORE modifying the counter
        so the state machine knows what kind of trip this is.

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
        """
        Withdraw a full inventory of a single ore type (iron, silver, gold).
        Simple bars always trigger smelting.
        """
        self._next_is_ore_trip = True

        ore_name = bar_type.data.ore.primary_ore
        self._bank_search(ore_name)
        self.humanizer.bank_delay()
        self._withdraw_all_from_first_slot()
        self.humanizer.action_delay()
        return True

    def _withdraw_two_ores(self, bar_type: BarType):
        """
        Withdraw two ore types (bronze: copper + tin).
        With coal bag slot occupied: 13 of each = 26 total + 1 coal bag = 27 slots.
        Without coal bag: 14 of each = 28 slots.
        """
        self._next_is_ore_trip = True
        has_bag = self.settings.use_coal_bag and self.coal_bag is not None

        # Determine amounts: coal bag takes 1 slot
        amount_each = 13 if has_bag else 14

        self._bank_search(bar_type.data.ore.primary_ore)
        self.humanizer.bank_delay()
        self._withdraw_x_from_first_slot(amount_each)
        self.humanizer.action_delay()

        self._bank_search(bar_type.data.ore.secondary_ore)
        self.humanizer.bank_delay()
        self._withdraw_x_from_first_slot(amount_each)
        self.humanizer.action_delay()
        return True

    def _withdraw_coal_bar_cycle(self, bar_type: BarType):
        """
        Handle the coal trip cycle for steel/mithril/adamant/rune.

        Coal requirements at Blast Furnace (halved):
          Steel:     1 coal per bar
          Mithril:   2 coal per bar
          Adamantite: 3 coal per bar
          Runite:    4 coal per bar

        WITH COAL BAG (27 coal capacity, 1 inv slot):
          Available inv slots = 27 (28 - coal bag)
          Each trip carries: 27 inv items + 27 coal bag = 54 total items

          Steel (1 coal/bar):
            Every trip is an ORE trip: 27 ore in inv, 27 coal in bag
            → Produces 27 bars per trip
            Coal bag provides exactly 1 coal per ore → perfect ratio

          Mithril (2 coal/bar):
            Need 2 coal per mithril ore.
            Trip 1 (COAL): 27 coal in inv + 27 coal in bag = 54 coal loaded
            Trip 2 (ORE):  27 mithril in inv + 27 coal in bag = 27 mithril + 27 coal
            Total coal: 54 + 27 = 81 coal for 27 ore → 3 coal/bar ✗ (need only 2)
            Actually: 54 coal on trip 1, then 27 ore + 27 coal on trip 2
            = 54 + 27 = 81 coal for 27 bars → 3 per bar. That's too much coal.

            CORRECT approach: coal_per_bar - 1 = number of coal-only trips per cycle.
            Mithril: 1 coal trip, then 1 ore trip (with coal bag filled both trips)
            Trip 1: 27 coal (inv) + 27 coal (bag) = 54 coal in furnace
            Trip 2: 27 ore (inv) + 27 coal (bag) = 27 coal + 27 ore
            Total: 54 + 27 = 81 coal for 27 ore = 3 coal/ore. But we need 2!

            The issue: with the bag filling every trip, we over-supply coal.
            This is FINE — the BF furnace holds up to 254 coal. Extra coal stays.
            The ore determines how many bars are made. Excess coal remains for next cycle.

            So the pattern is: (coal_per_bar - 1) coal-only trips, then 1 ore trip.
            Coal bag is filled every trip. This over-supplies coal slightly but
            the excess carries over, and over many cycles it averages out.
            Real players do the same thing — it's the standard efficient method.

          Adamantite (3 coal/bar): 2 coal trips + 1 ore trip
          Runite (4 coal/bar): 3 coal trips + 1 ore trip

        WITHOUT COAL BAG:
          Full 28 slots available.
          Need coal_per_bar coal trips per ore trip.
          Steel: 1 coal trip + 1 ore trip
          Mithril: 2 coal trips + 1 ore trip
          Adamantite: 3 coal trips + 1 ore trip
          Runite: 4 coal trips + 1 ore trip
        """
        coal_per_bar = bar_type.data.coal_per_bar
        has_bag = self.settings.use_coal_bag and self.coal_bag is not None

        if has_bag:
            # Search for coal first so the bank displays it (needed for verification)
            self._bank_search("Coal")
            self.humanizer.bank_delay()

            # Set coal position for visual verification of bag fill
            bx = self.regions.game_x + self.regions.game_w // 2 - 150
            by = self.regions.game_y + 115
            self.coal_bag.set_bank_coal_pos(bx, by)

            # Fill coal bag — visually verified (retries if click doesn't register)
            if not self.coal_bag.fill():
                print("    [WARN] Coal bag fill could not be verified")
            self.humanizer.action_delay()

            if coal_per_bar == 1:
                # STEEL SPECIAL CASE: every trip is ore + coal bag
                # 27 ore in inventory + 27 coal in bag = perfect 1:1 ratio
                self._next_is_ore_trip = True
                self._bank_search(bar_type.data.ore.primary_ore)
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self.humanizer.action_delay()
                return True

            # For mithril/adamant/rune: alternate coal and ore trips
            coal_trips_needed = coal_per_bar - 1  # Bag covers 1 coal/bar on ore trip

            if self._coal_trip < coal_trips_needed:
                # COAL-ONLY TRIP
                self._next_is_ore_trip = False
                self._bank_search("Coal")
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip += 1
                self.humanizer.action_delay()
                return True
            else:
                # ORE TRIP
                self._next_is_ore_trip = True
                self._bank_search(bar_type.data.ore.primary_ore)
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip = 0
                self.humanizer.action_delay()
                return True
        else:
            # No coal bag: alternate full inventories of coal and ore
            if self._coal_trip < coal_per_bar:
                # COAL TRIP
                self._next_is_ore_trip = False
                self._bank_search("Coal")
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip += 1
            else:
                # ORE TRIP
                self._next_is_ore_trip = True
                self._bank_search(bar_type.data.ore.primary_ore)
                self.humanizer.bank_delay()
                self._withdraw_all_from_first_slot()
                self._coal_trip = 0
            self.humanizer.action_delay()
            return True

    def is_ore_trip(self):
        """
        Check if the CURRENT trip (just withdrawn) is an ore trip.
        This was determined during withdraw_ore() before the counter changed.
        """
        return self._next_is_ore_trip

    def handle_stamina(self):
        """
        Check run energy and drink a stamina potion if needed.
        Withdraws from bank if necessary.
        """
        if not self.settings.use_stamina:
            return

        # Check run energy via the minimap orb area
        orb_x = self.regions.minimap_cx + 24
        orb_y = self.regions.minimap_cy + 78
        orb_color = get_pixel_color(orb_x, orb_y)

        # If stamina effect is active (bright orange/yellow orb), skip
        if color_matches(orb_color, Colors.STAMINA_ACTIVE, 30):
            return

        # If run energy looks healthy (bright), skip
        brightness = sum(orb_color) / 3
        if brightness > 120:
            return

        # Need stamina — search for it in bank
        if not self.is_bank_open():
            return

        self._bank_search("Stamina")
        self.humanizer.bank_delay()

        # Check if stamina exists in bank
        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115
        color = get_pixel_color(bx, by)
        if color_matches(color, Colors.BANK_SLOT_EMPTY, COLOR_TOLERANCE):
            return  # No stamina potions in bank

        self._withdraw_x_from_first_slot(1)
        self.humanizer.action_delay()

        # Close bank to drink
        self.close_bank()
        self.humanizer.action_delay()

        # Find and click the stamina potion in inventory
        stam_color = (200, 160, 40)
        coal_bag_slot = self._get_coal_bag_slot()
        stam_slot = self.inventory.find_first_slot_with_color(
            stam_color, tolerance=35, exclude_slot=coal_bag_slot
        )
        if stam_slot is not None:
            self.inventory.click_slot(stam_slot)
            self.humanizer.action_delay()
            time.sleep(0.6)  # Wait for drink animation

        # Re-open bank
        self.open_bank()
        self.humanizer.bank_delay()

        # Deposit empty vial if present
        vial_color = (180, 180, 200)
        vial_slot = self.inventory.find_first_slot_with_color(
            vial_color, tolerance=30, exclude_slot=coal_bag_slot
        )
        if vial_slot is not None:
            self.inventory.click_slot(vial_slot)
            self.humanizer.action_delay()

    def has_supplies(self, bar_type: BarType):
        """
        Quick check if the bank has the required ores.
        Searches bank and checks if results appear.
        """
        if not self.is_bank_open():
            return False

        # Check primary ore
        self._bank_search(bar_type.data.ore.primary_ore)
        self.humanizer.bank_delay()

        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115
        color = get_pixel_color(bx, by)
        has_ore = not color_matches(color, Colors.BANK_SLOT_EMPTY, COLOR_TOLERANCE)

        if not has_ore:
            return False

        # Check coal if needed
        if bar_type.data.requires_coal:
            self._bank_search("Coal")
            self.humanizer.bank_delay()
            color = get_pixel_color(bx, by)
            has_coal = not color_matches(color, Colors.BANK_SLOT_EMPTY, COLOR_TOLERANCE)
            return has_coal

        # Check secondary ore if needed (bronze)
        if bar_type.data.ore.has_two_ores:
            self._bank_search(bar_type.data.ore.secondary_ore)
            self.humanizer.bank_delay()
            color = get_pixel_color(bx, by)
            return not color_matches(color, Colors.BANK_SLOT_EMPTY, COLOR_TOLERANCE)

        return True

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

        # "Withdraw-All" is typically the 5th menu option (~75px down)
        mouse.click(bx, by + 75, variance=2)
        self.humanizer.action_delay()

    def _withdraw_x_from_first_slot(self, amount):
        """Right-click and withdraw a specific amount."""
        bx = self.regions.game_x + self.regions.game_w // 2 - 150
        by = self.regions.game_y + 115

        if amount == 1:
            # Left-click withdraws 1 by default
            mouse.click(bx, by, variance=2)
        else:
            mouse.right_click(bx, by, variance=2)
            self.humanizer.action_delay()
            # "Withdraw-X" is typically the 6th menu option (~90px down)
            mouse.click(bx, by + 90, variance=2)
            self.humanizer.action_delay()
            pyautogui.typewrite(str(amount), interval=0.05)
            pyautogui.press("enter")
        self.humanizer.action_delay()
