"""
Furnace interaction handler.

Handles:
- Clicking the conveyor belt to deposit ores
- Emptying coal bag at conveyor
- Walking between conveyor, dispenser, and bank via minimap
- Detecting when bars are ready at the dispenser
- Collecting bars (press SPACE or click dispenser with ice gloves)
- Glove swapping (goldsmith gauntlets <-> ice gloves)

Key Blast Furnace mechanics:
- Conveyor belt left-click: "Put-ore-on" deposits all matching ores from inventory
- Coal bag: left-click empties coal INTO INVENTORY, then must click conveyor again
- Bar dispenser: click "Take" to collect bars. With ice gloves, bars go straight
  to inventory. Without ice gloves, you need a bucket of water to cool them first.
- The dispenser is only interactable when bars are ready. Before that it shows
  "The bars are still too hot" or simply has no "Take" option.
- Bars smelt ~2 ticks after ore hits the conveyor (nearly instant on BF worlds).
- For coal-requiring bars: ALL coal must be in the furnace BEFORE the primary ore
  is deposited, otherwise you get wrong bars (e.g., iron instead of steel).
"""

import time
import pyautogui
from config import ScreenRegions, Colors, COLOR_TOLERANCE, BotSettings
from screen.capture import (
    capture_region, color_matches, get_pixel_color,
    region_has_color, get_pixel_color_from_frame,
    count_color_in_region,
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
        # Track the screen state from the previous frame for idle detection
        self._prev_viewport_sample = None

    def _get_coal_bag_slot(self):
        """Safely get coal bag slot, returns None if no coal bag."""
        if self.coal_bag is not None:
            return self.coal_bag.get_locked_slot()
        return None

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
        The game viewport changes when the player moves (camera follows player).
        """
        start = time.time()

        # Sample a small area of the game viewport center
        sample_x = self.regions.game_x + self.regions.game_w // 2 - 20
        sample_y = self.regions.game_y + self.regions.game_h // 2 - 20
        sample_w, sample_h = 40, 40

        prev_sample = capture_region(sample_x, sample_y, sample_w, sample_h)
        stable_count = 0

        while time.time() - start < timeout:
            time.sleep(0.35)
            curr_sample = capture_region(sample_x, sample_y, sample_w, sample_h)

            # Compare frames: if mostly the same, player is idle
            import numpy as np
            diff = np.mean(np.abs(curr_sample.astype(float) - prev_sample.astype(float)))

            if diff < 5.0:
                stable_count += 1
                if stable_count >= 2:
                    # Two consecutive stable frames = player stopped
                    self.humanizer.action_delay()
                    return True
            else:
                stable_count = 0

            prev_sample = curr_sample

        return False

    # ── Run energy ──

    def ensure_run_enabled(self):
        """
        Check if run is enabled and toggle it on if not.
        The run orb is near the minimap. When run is off, the orb icon is darker.
        """
        # Run orb is typically to the right/below the minimap
        orb_x = self.regions.minimap_cx + 24
        orb_y = self.regions.minimap_cy + 78
        color = get_pixel_color(orb_x, orb_y)

        # When run is ON, the orb has a brighter yellow/green tint
        # When OFF, it's much darker/grey
        brightness = sum(color) / 3
        if brightness < 100:
            # Run appears to be off — click the orb to toggle
            mouse.click(orb_x, orb_y, variance=2)
            self.humanizer.action_delay()

    # ── Conveyor belt ──

    def click_conveyor(self):
        """
        Click the conveyor belt to deposit ores.
        Left-click action is "Put-ore-on" which deposits all ores from inventory.
        """
        cx, cy = self.regions.conveyor_pos
        mouse.click(cx, cy, variance=4)
        self.humanizer.reaction_delay()

    def deposit_on_conveyor(self, bar_type: BarType, is_ore_trip: bool):
        """
        Full conveyor deposit sequence. The order matters critically for
        coal-requiring bars:

        FOR COAL-ONLY TRIPS:
          1. Click conveyor (deposits coal from inventory)
          2. Empty coal bag (coal goes to inventory)
          3. Click conveyor again (deposits coal bag coal)

        FOR ORE TRIPS (coal-requiring bars):
          1. Empty coal bag first (coal goes to inventory)
          2. Click conveyor (deposits coal from bag + ore from inventory)
          OR if coal bag was already emptied:
          1. Click conveyor (deposits ore)

        FOR SIMPLE BARS (no coal):
          1. Click conveyor (deposits ore)

        Returns True when inventory is clear of ores.
        """
        coal_bag_slot = self._get_coal_bag_slot()

        if bar_type.data.requires_coal and self.coal_bag is not None and not self.coal_bag.is_empty:
            # Has coal in the bag — need to handle it

            if not is_ore_trip:
                # COAL-ONLY TRIP: deposit inventory coal first, then bag coal
                self.click_conveyor()
                self._wait_for_deposit(timeout=3.0)
                self.humanizer.action_delay()

                # Empty coal bag → coal goes to inventory
                self.coal_bag.empty()
                self.humanizer.action_delay()

                # Deposit the coal that came from the bag
                if not self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                    self.click_conveyor()
                    self._wait_for_deposit(timeout=3.0)
            else:
                # ORE TRIP: empty coal bag first so coal goes in before ore
                # This ensures coal is deposited before primary ore
                self.coal_bag.empty()
                self.humanizer.action_delay()

                # Now click conveyor — deposits both coal (from bag) and ore together
                self.click_conveyor()
                self._wait_for_deposit(timeout=3.0)

                # If anything remains (shouldn't normally), click again
                if not self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                    self.humanizer.action_delay()
                    self.click_conveyor()
                    self._wait_for_deposit(timeout=3.0)
        else:
            # Simple deposit — no coal bag involved
            self.click_conveyor()
            self._wait_for_deposit(timeout=3.0)

        # Verify inventory is clear
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

        Detection: The bar dispenser changes visually when bars are ready.
        The dispenser object gets a glow or the bars become visible on top.
        We sample the area around the dispenser position for the glow color.
        """
        dx, dy = self.regions.dispenser_pos
        frame = capture_region(dx - 25, dy - 25, 50, 50)
        offset = (dx - 25, dy - 25)

        # Check for the characteristic bar-ready glow/shine
        return region_has_color(
            frame, Colors.BAR_READY_GLOW,
            dx - 20, dy - 20, dx + 20, dy + 20,
            tolerance=30, min_pixels=8, region_offset=offset
        )

    def click_dispenser(self):
        """
        Click the bar dispenser. Left-click action is "Take" when bars are ready.
        When no bars are ready, the dispenser shows "Check" or is not interactable
        for taking — clicking it does nothing useful.
        """
        dx, dy = self.regions.dispenser_pos
        mouse.click(dx, dy, variance=4)
        self.humanizer.reaction_delay()

    def collect_bars(self, bar_type: BarType):
        """
        Collect bars from the bar dispenser.

        With ice gloves (or Smiths gloves (i)) equipped:
          - Click dispenser → "Take" → bars go directly to inventory
          - May need to press SPACE or click on the bar in the interface

        Without ice gloves:
          - Need bucket of water to cool bars first (not recommended)

        The collection interface shows a bar icon. Press SPACE or click the
        bar to collect all available bars.

        Returns number of bars collected (0 if failed).
        """
        coal_bag_slot = self._get_coal_bag_slot()

        # Count items before collection
        items_before = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)

        # Click dispenser
        self.click_dispenser()

        # Wait for the collection interface / bars to enter inventory
        # The dispenser interaction has a short delay
        time.sleep(0.8)
        self.humanizer.action_delay()

        # Press SPACE to confirm collection (this is the standard BF interaction)
        pyautogui.press("space")
        self.humanizer.reaction_delay()

        # Wait for bars to appear in inventory
        time.sleep(0.6)
        items_after = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)
        collected = max(0, items_after - items_before)

        # If first attempt didn't work, try clicking the bar collect button
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
        Wait for bars to finish smelting at the dispenser.
        Bars at the BF smelt in ~2 game ticks after ore is deposited.
        The dispenser becomes interactable only when bars are done.
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.are_bars_ready():
                self.humanizer.action_delay()
                return True
            time.sleep(0.4)
        # Even if detection fails, bars are almost certainly ready after 5s
        return False

    # ── Glove management ──

    def swap_to_ice_gloves(self):
        """
        Equip ice gloves before collecting bars.
        Ice gloves auto-cool the bars so they go directly to inventory.
        Click the ice gloves in inventory to equip them.
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
        Must be worn when the gold bar XP is awarded (on deposit).
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
