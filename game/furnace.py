"""
Furnace interaction handler.

Handles:
- Clicking the conveyor belt to deposit ores
- Emptying coal bag at conveyor (left-click = "Empty" when bank is closed)
- Walking between conveyor, dispenser, and bank via minimap
- Detecting when bars are ready at the dispenser
- Collecting bars (click dispenser "Take", press SPACE to collect all)
- Glove swapping (goldsmith gauntlets <-> ice gloves)

Key Blast Furnace mechanics (from OSRS wiki + gameplay):
- Conveyor belt left-click: "Put-ore-on" deposits all ores from inventory
- Coal bag: LEFT-CLICK at conveyor = "Empty" (dumps coal to inventory).
  LEFT-CLICK in bank = "Fill". The context determines the action.
- Bar dispenser:
  - Click dispenser → dialogue/collection window opens → press SPACE to take all
  - With ice gloves: bars go directly to inventory (auto-cooled)
  - Without ice gloves: need bucket of water to cool first
  - The dispenser does NOT work while a dialogue box is already open
  - If no bars are ready, clicking does nothing useful
- Bars smelt ~11 ticks (~6.6s) after ore hits the conveyor (variable delay)
- ALL coal must be in furnace BEFORE primary ore for coal-requiring bars
- Max 28 bars stored in dispenser at once
- The efficient pattern: bank → walk to conveyor → deposit ore on conveyor
  (frees inventory) → empty coal bag → deposit coal → walk to dispenser →
  collect PREVIOUS bars (inventory now empty) → walk back to bank.
  Bars smelt while banking, so zero idle wait after the first trip.
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
from game.object_finder import ObjectFinder
from input import mouse
from anti_detect.humanizer import Humanizer
from data.bars import BarType


class FurnaceHandler:
    """
    All furnace-area interactions: conveyor belt, bar dispenser, navigation.
    Uses RuneLite Object Markers to find objects dynamically.
    """

    def __init__(self, regions: ScreenRegions, settings: BotSettings,
                 inventory: InventoryReader, coal_bag, humanizer: Humanizer):
        self.regions = regions
        self.settings = settings
        self.inventory = inventory
        self.coal_bag = coal_bag  # Can be None if not using coal bag
        self.humanizer = humanizer
        self.finder = ObjectFinder(regions)

        # Whether we've primed the furnace (first trip has no bars to collect)
        self._primed = False

        # Whether we need to preload coal before first ore trip
        # (for steel/mithril/adamant/rune on the very first cycle)
        self._coal_preloaded = False

        # Glove tracking: True = goldsmith gauntlets equipped, False = ice gloves equipped.
        # Assumes goldsmith gauntlets start equipped (standard setup).
        self._goldsmith_equipped = settings.use_goldsmith_gauntlets

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

    # ── Navigation via color markers ──
    # Instead of minimap (useless on mass worlds), click the RuneLite
    # color-marked objects directly in the viewport. The character
    # auto-walks to any object you left-click.

    def walk_to_bank(self):
        """Click the bank chest color marker to walk and interact."""
        bx, by = self.finder.find_bank()
        mouse.click(bx, by, variance=4)
        self.humanizer.walk_delay()
        self._wait_until_idle(timeout=6.0)

    def walk_to_conveyor(self):
        """Click the conveyor belt color marker to walk and interact."""
        cx, cy = self.finder.find_conveyor()
        mouse.click(cx, cy, variance=4)
        self.humanizer.walk_delay()
        self._wait_until_idle(timeout=6.0)

    def walk_to_dispenser(self):
        """Click the bar dispenser color marker to walk and interact."""
        dx, dy = self.finder.find_dispenser()
        mouse.click(dx, dy, variance=4)
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
        Toggle run on if it's off. Uses the calibrated run orb position.
        """
        orb_x, orb_y = self.regions.run_orb_pos
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
        Finds the conveyor via RuneLite yellow marker.
        """
        cx, cy = self.finder.find_conveyor()
        mouse.click(cx, cy, variance=4)
        self.humanizer.reaction_delay()

    def deposit_on_conveyor(self, bar_type: BarType, is_ore_trip: bool):
        """
        Full conveyor deposit sequence.

        CRITICAL: Coal must be in the furnace BEFORE ore for correct bars.
        However, the conveyor belt transports items to the melting pot together.
        Items deposited within a few ticks arrive together before smelting starts.
        For the first trip, coal from the bag follows ore closely on the belt.
        For subsequent trips, coal from previous trips is already in the furnace.

        FOR COAL-ONLY TRIPS:
          1. Click conveyor (deposits coal from inventory)
          2. Left-click coal bag (empties coal to inventory, bank is closed)
          3. Click conveyor again (deposits coal from bag)

        FOR ORE TRIPS (coal-requiring bars with coal bag):
          Inventory is FULL (27 ore + 1 coal bag slot). Can't empty bag first!
          1. Click conveyor (deposits 27 ore, frees inventory)
          2. Left-click coal bag (empties coal into now-empty inventory)
          3. Click conveyor again (deposits coal from bag)
          The coal follows the ore on the belt and arrives at the pot
          before smelting starts (~2 game ticks). Plus, previous trips'
          coal is already in the furnace.

        FOR SIMPLE BARS (no coal needed):
          1. Click conveyor (deposits ore)

        Returns True when inventory is clear.
        """
        coal_bag_slot = self._get_coal_bag_slot()
        has_coal_bag = self.coal_bag is not None and self.settings.use_coal_bag

        if bar_type.data.requires_coal and has_coal_bag:
            if not is_ore_trip:
                # COAL-ONLY TRIP
                # Step 1: deposit inventory coal
                self.click_conveyor()
                self._wait_for_deposit(timeout=3.0)
                self.humanizer.action_delay()

                # Step 2: left-click coal bag to empty into inventory
                self.coal_bag.empty_at_conveyor()
                self.humanizer.action_delay()

                # Step 3: deposit the coal that came from bag
                if not self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                    self.click_conveyor()
                    self._wait_for_deposit(timeout=3.0)
            else:
                # ORE TRIP with coal bag
                # Inventory is FULL (27 ore + coal bag). Must deposit ore first!

                # Step 1: Click conveyor — deposits 27 ore (frees inventory)
                self.click_conveyor()
                self._wait_for_deposit(timeout=3.0)
                self.humanizer.action_delay()

                # Step 2: Left-click coal bag — empties coal into inventory
                self.coal_bag.empty_at_conveyor()
                self.humanizer.action_delay()

                # Step 3: Click conveyor again — deposits coal from bag
                if not self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
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
        color change around the dispenser. Uses the dynamically-found
        dispenser position.
        """
        dx, dy = self.finder.find_dispenser()
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
        Finds the dispenser via RuneLite magenta marker.
        """
        dx, dy = self.finder.find_dispenser()
        mouse.click(dx, dy, variance=4)
        self.humanizer.reaction_delay()

    def collect_bars(self, bar_type: BarType):
        """
        Collect bars from the bar dispenser.

        Flow:
        1. Click dispenser (left-click = "Take")
        2. A dialogue/collection window opens
        3. Press SPACE to collect all bars
        4. Poll inventory until bars appear (dynamic wait, no static sleep)

        Note: The dispenser does NOT work while a dialogue box is already open.
        If a stale dialogue is blocking, we dismiss it first with SPACE.

        Returns number of bars collected (0 if failed).
        """
        coal_bag_slot = self._get_coal_bag_slot()
        items_before = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)

        # Dismiss any blocking dialogue that might prevent dispenser interaction
        pyautogui.press("space")
        time.sleep(0.15)

        # Step 1: Click dispenser to open collection interface
        self.click_dispenser()

        # Step 2: Wait for collection dialogue (poll, not static sleep)
        self._poll_for_dialogue(timeout=2.0)
        self.humanizer.action_delay()

        # Step 3: Press SPACE to collect all bars
        pyautogui.press("space")

        # Step 4: Poll inventory for bars appearing (dynamic wait)
        collected = self._poll_for_bars_in_inventory(
            items_before, coal_bag_slot, timeout=3.0
        )

        # Fallback: if SPACE didn't register, try pressing SPACE again
        if collected == 0:
            self.humanizer.action_delay()
            pyautogui.press("space")

            collected = self._poll_for_bars_in_inventory(
                items_before, coal_bag_slot, timeout=2.0
            )

        return collected

    def _poll_for_bars_in_inventory(self, items_before, exclude_slot, timeout=3.0):
        """
        Poll inventory until bar items appear. Returns count of new items.
        Triggers transition as soon as items are detected — saves milliseconds
        per trip and looks more human than static sleeps.
        """
        start = time.time()
        while time.time() - start < timeout:
            items_now = self.inventory.count_filled_slots(exclude_slot=exclude_slot)
            collected = items_now - items_before
            if collected > 0:
                # Brief extra wait for remaining bars to finish transferring
                time.sleep(0.15)
                items_final = self.inventory.count_filled_slots(exclude_slot=exclude_slot)
                return max(0, items_final - items_before)
            time.sleep(0.1)
        return 0

    def _poll_for_dialogue(self, timeout=2.0):
        """
        Poll for the collection dialogue to appear after clicking dispenser.
        Detects the dialogue by checking for the characteristic widget background
        color at the center of the game viewport (where the widget appears).
        """
        start = time.time()
        # The collection widget appears near the center of the viewport
        wx = self.regions.game_x + self.regions.game_w // 2
        wy = self.regions.game_y + self.regions.game_h // 2
        while time.time() - start < timeout:
            color = get_pixel_color(wx, wy)
            if color_matches(color, Colors.DISPENSER_WIDGET_BG, 25):
                return True
            time.sleep(0.1)
        return False

    def wait_for_bars(self, timeout=8.0):
        """
        Wait for bars to finish smelting. Bars smelt in ~11 game ticks (~6.6s).
        The delay is somewhat variable. Only needed on first trip (priming);
        after that, pipelining ensures bars are always ready before we arrive.
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
    #
    # Gloves occupy a LOCKED inventory slot (settings.glove_slot).
    # One pair is equipped, the other sits in the locked slot.
    # Clicking the slot equips the inventory pair and puts the
    # equipped pair back in the slot. Simple swap.

    def swap_gloves(self):
        """
        Click the locked glove slot to swap between equipped and inventory gloves.

        If goldsmith is equipped → click slot → ice gloves equip, goldsmith to slot.
        If ice gloves equipped → click slot → goldsmith equip, ice gloves to slot.

        Used before depositing ore (need goldsmith) and before collecting bars (need ice).
        """
        glove_slot = self.settings.glove_slot
        self.inventory.click_slot(glove_slot)
        self.humanizer.action_delay()

    def swap_to_ice_gloves(self):
        """
        Ensure ice gloves are equipped before collecting bars.

        We track which gloves are equipped via _goldsmith_equipped flag.
        If goldsmith is currently equipped, swap. If ice already equipped, skip.
        """
        if not self.settings.use_ice_gloves:
            return

        if self._goldsmith_equipped:
            self.swap_gloves()
            self._goldsmith_equipped = False

    def swap_to_goldsmith_gauntlets(self):
        """
        Ensure goldsmith gauntlets are equipped before depositing gold ore.

        If ice gloves are currently equipped, swap. If goldsmith already equipped, skip.
        """
        if not self.settings.use_goldsmith_gauntlets:
            return

        if not self._goldsmith_equipped:
            self.swap_gloves()
            self._goldsmith_equipped = True
