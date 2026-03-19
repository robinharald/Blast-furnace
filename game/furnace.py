"""
Furnace interaction handler.

Handles:
- Clicking the conveyor belt to deposit ores
- Emptying coal bag at conveyor (shift-click)
- Walking between conveyor, dispenser, and bank via minimap
- Detecting when bars are ready at the dispenser
- Collecting bars (click dispenser "Take", then SPACE to confirm)
- Glove swapping (goldsmith gauntlets <-> ice gloves)

Key Blast Furnace mechanics (from OSRS wiki):
- Conveyor belt left-click: "Put-ore-on" deposits all ores from inventory
- Coal bag: SHIFT-CLICK at conveyor empties coal into inventory, then click conveyor
- Bar dispenser has 4 states: Empty, Pouring, Hot, Cooled
  - "Take" option only in Hot and Cooled states
  - Pouring state: NO interaction possible, must wait
  - With ice gloves: click "Take" and bars go to inventory
  - Without ice gloves: need bucket of water first
- Bars smelt ~2 ticks after ore hits the conveyor
- ALL coal must be in furnace BEFORE primary ore for coal-requiring bars
- Max 28 bars stored in dispenser at once
- The efficient pattern: collect PREVIOUS batch first, then deposit new ore
  (eliminates smelting wait time)
"""

import time
import pyautogui
import numpy as np
from config import ScreenRegions, Colors, COLOR_TOLERANCE, BotSettings
from screen.capture import (
    capture_region, color_matches, get_pixel_color,
    region_has_color, get_pixel_color_from_frame,
)
from game.inventory import InventoryReader
from input import mouse
from anti_detect.humanizer import Humanizer
from data.bars import BarType


class FurnaceHandler:
    """
    All furnace-area interactions: conveyor belt, bar dispenser, navigation.
    """

    def __init__(self, regions: ScreenRegions, settings: BotSettings,
                 inventory: InventoryReader, coal_bag, humanizer: Humanizer):
        self.regions = regions
        self.settings = settings
        self.inventory = inventory
        self.coal_bag = coal_bag  # Can be None if not using coal bag
        self.humanizer = humanizer

        # Whether we've primed the furnace (first trip has no bars to collect)
        self._primed = False

        # Whether we need to preload coal before first ore trip
        # (for steel/mithril/adamant/rune on the very first cycle)
        self._coal_preloaded = False

    def _get_coal_bag_slot(self):
        """Safely get coal bag slot, returns None if no coal bag."""
        if self.coal_bag is not None:
            return self.coal_bag.get_locked_slot()
        return None

    @property
    def is_primed(self):
        """Whether the furnace has been primed (previous bars exist to collect)."""
        return self._primed

    def mark_primed(self):
        """Mark that bars now exist in the dispenser from a previous deposit."""
        self._primed = True

    @property
    def coal_preloaded(self):
        return self._coal_preloaded

    def mark_coal_preloaded(self):
        self._coal_preloaded = True

    # ── Navigation via minimap ──

    def walk_to_bank(self):
        """Click minimap to walk toward the bank chest."""
        mx, my = self.regions.minimap_bank
        mouse.click(mx, my, variance=3)
        self.humanizer.walk_delay()
        self._wait_until_idle(timeout=6.0)

    def walk_to_conveyor(self):
        """Click minimap to walk toward the conveyor belt."""
        mx, my = self.regions.minimap_conveyor
        mouse.click(mx, my, variance=3)
        self.humanizer.walk_delay()
        self._wait_until_idle(timeout=6.0)

    def walk_to_dispenser(self):
        """Click minimap to walk toward the bar dispenser."""
        mx, my = self.regions.minimap_dispenser
        mouse.click(mx, my, variance=3)
        self.humanizer.walk_delay()
        self._wait_until_idle(timeout=6.0)

    def _wait_until_idle(self, timeout=5.0):
        """
        Wait until the player stops moving.
        Detects movement by comparing viewport pixel samples between frames.
        """
        start = time.time()
        sample_x = self.regions.game_x + self.regions.game_w // 2 - 20
        sample_y = self.regions.game_y + self.regions.game_h // 2 - 20
        sample_w, sample_h = 40, 40

        prev_sample = capture_region(sample_x, sample_y, sample_w, sample_h)
        stable_count = 0

        while time.time() - start < timeout:
            time.sleep(0.35)
            curr_sample = capture_region(sample_x, sample_y, sample_w, sample_h)

            diff = np.mean(np.abs(curr_sample.astype(float) - prev_sample.astype(float)))

            if diff < 5.0:
                stable_count += 1
                if stable_count >= 2:
                    self.humanizer.action_delay()
                    return True
            else:
                stable_count = 0

            prev_sample = curr_sample

        return False

    # ── Run energy ──

    def ensure_run_enabled(self):
        """
        Toggle run on if it's off. The run orb is near the minimap.
        """
        orb_x = self.regions.minimap_cx + 24
        orb_y = self.regions.minimap_cy + 78
        color = get_pixel_color(orb_x, orb_y)

        brightness = sum(color) / 3
        if brightness < 100:
            mouse.click(orb_x, orb_y, variance=2)
            self.humanizer.action_delay()

    # ── Conveyor belt ──

    def click_conveyor(self):
        """
        Click the conveyor belt. Left-click = "Put-ore-on".
        Deposits all ores/coal from inventory onto the belt.
        """
        cx, cy = self.regions.conveyor_pos
        mouse.click(cx, cy, variance=4)
        self.humanizer.reaction_delay()

    def deposit_on_conveyor(self, bar_type: BarType, is_ore_trip: bool):
        """
        Full conveyor deposit sequence.

        CRITICAL ORDER FOR COAL BARS:
        Coal must be in the furnace BEFORE ore. If iron is deposited without
        coal, you get iron bars instead of steel. The coal bag coal must
        be emptied and deposited BEFORE the primary ore.

        FOR COAL-ONLY TRIPS:
          1. Click conveyor (deposits coal from inventory)
          2. Shift-click coal bag (empties coal to inventory)
          3. Click conveyor again (deposits coal from bag)

        FOR ORE TRIPS (coal-requiring bars with coal bag):
          1. Shift-click coal bag (empties coal to inventory)
          2. Click conveyor (deposits coal from bag + primary ore together)
             The coal goes in first since it's earlier in inventory slots.

        FOR SIMPLE BARS (no coal needed):
          1. Click conveyor (deposits ore)

        Returns True when inventory is clear.
        """
        coal_bag_slot = self._get_coal_bag_slot()
        has_coal_bag = self.coal_bag is not None and self.settings.use_coal_bag

        if bar_type.data.requires_coal and has_coal_bag and not self.coal_bag.is_empty:
            if not is_ore_trip:
                # COAL-ONLY TRIP
                # Step 1: deposit inventory coal
                self.click_conveyor()
                self._wait_for_deposit(timeout=3.0)
                self.humanizer.action_delay()

                # Step 2: shift-click coal bag to empty into inventory
                self.coal_bag.empty_at_conveyor()
                self.humanizer.action_delay()

                # Step 3: deposit the coal that came from bag
                if not self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                    self.click_conveyor()
                    self._wait_for_deposit(timeout=3.0)
            else:
                # ORE TRIP with coal bag
                # Step 1: shift-click coal bag first (coal goes to inventory)
                self.coal_bag.empty_at_conveyor()
                self.humanizer.action_delay()

                # Step 2: click conveyor — deposits everything
                # Coal from bag + ore from bank both go onto conveyor
                self.click_conveyor()
                self._wait_for_deposit(timeout=3.0)

                # Step 3: safety — if anything remains, click again
                if not self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                    self.humanizer.action_delay()
                    self.click_conveyor()
                    self._wait_for_deposit(timeout=3.0)
        else:
            # Simple deposit — no coal bag or no coal in bag
            self.click_conveyor()
            self._wait_for_deposit(timeout=3.0)

        return self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot)

    def _wait_for_deposit(self, timeout=3.0):
        """Wait for the conveyor deposit animation to complete."""
        start = time.time()
        coal_bag_slot = self._get_coal_bag_slot()

        while time.time() - start < timeout:
            if self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                return True
            time.sleep(0.3)

        return False

    # ── Bar dispenser ──

    def are_bars_ready(self):
        """
        Check if bars are ready to collect at the dispenser.

        The bar dispenser has 4 states:
        - Empty: no bars, only "Check" option
        - Pouring: bars being smelted, NO interaction possible
        - Hot: bars ready but hot, "Take" option available (need ice gloves)
        - Cooled: bars ready and cooled, "Take" option available

        We detect the Hot/Cooled state by checking for a visual glow or
        color change around the dispenser.
        """
        dx, dy = self.regions.dispenser_pos
        frame = capture_region(dx - 25, dy - 25, 50, 50)
        offset = (dx - 25, dy - 25)

        return region_has_color(
            frame, Colors.BAR_READY_GLOW,
            dx - 20, dy - 20, dx + 20, dy + 20,
            tolerance=30, min_pixels=8, region_offset=offset
        )

    def click_dispenser(self):
        """
        Click the bar dispenser. Left-click = "Take" when bars are ready.
        When empty or pouring, clicking does nothing useful.
        """
        dx, dy = self.regions.dispenser_pos
        mouse.click(dx, dy, variance=4)
        self.humanizer.reaction_delay()

    def collect_bars(self, bar_type: BarType):
        """
        Collect bars from the bar dispenser.

        Flow:
        1. Click dispenser ("Take")
        2. If a confirmation dialogue appears, press SPACE to confirm
        3. Bars transfer to inventory

        With ice gloves equipped, bars go straight to inventory.
        The SPACE press handles any dialogue that may appear.

        Returns number of bars collected (0 if failed).
        """
        coal_bag_slot = self._get_coal_bag_slot()
        items_before = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)

        # Click dispenser
        self.click_dispenser()

        # Wait for interaction to process
        time.sleep(0.8)
        self.humanizer.action_delay()

        # Press SPACE to confirm any dialogue
        pyautogui.press("space")
        self.humanizer.reaction_delay()

        # Wait for bars to appear in inventory
        time.sleep(0.6)
        items_after = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)
        collected = max(0, items_after - items_before)

        # Fallback: if SPACE didn't work, try clicking the collect button
        if collected == 0:
            bx, by = self.regions.bar_collect_btn
            mouse.click(bx, by, variance=3)
            self.humanizer.reaction_delay()
            time.sleep(0.5)
            items_after = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)
            collected = max(0, items_after - items_before)

        return collected

    def wait_for_bars(self, timeout=5.0):
        """
        Wait for bars to finish smelting. Bars smelt in ~2 game ticks.
        During the "Pouring" state the dispenser is not interactable.
        We poll until the Hot/Cooled state is detected.
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.are_bars_ready():
                self.humanizer.action_delay()
                return True
            time.sleep(0.4)
        # After timeout, bars are almost certainly ready
        return False

    # ── Glove management ──

    def swap_to_ice_gloves(self):
        """
        Equip ice gloves before collecting bars.
        Ice gloves auto-cool bars on collection.
        """
        if not self.settings.use_ice_gloves:
            return

        ice_glove_color = (150, 180, 220)
        coal_bag_slot = self._get_coal_bag_slot()

        slot = self.inventory.find_first_slot_with_color(
            ice_glove_color, tolerance=35, exclude_slot=coal_bag_slot
        )
        if slot is not None:
            self.inventory.click_slot(slot)
            self.humanizer.action_delay()

    def swap_to_goldsmith_gauntlets(self):
        """
        Equip goldsmith gauntlets for gold ore XP bonus.
        Must be worn when gold ore is deposited on conveyor.
        """
        if not self.settings.use_goldsmith_gauntlets:
            return

        gauntlet_color = (180, 150, 50)
        coal_bag_slot = self._get_coal_bag_slot()

        slot = self.inventory.find_first_slot_with_color(
            gauntlet_color, tolerance=35, exclude_slot=coal_bag_slot
        )
        if slot is not None:
            self.inventory.click_slot(slot)
            self.humanizer.action_delay()
