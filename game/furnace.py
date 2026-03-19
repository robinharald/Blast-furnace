"""
Furnace interaction handler.

Handles:
- Clicking the conveyor belt to deposit ores
- Emptying coal bag at conveyor
- Walking between conveyor, dispenser, and bank via minimap
- Detecting when bars are ready at the dispenser
- Collecting bars from the dispenser widget
- Glove swapping (goldsmith gauntlets <-> ice gloves)
"""

import time
from config import ScreenRegions, Colors, COLOR_TOLERANCE, BotSettings
from screen.capture import (
    capture_region, color_matches, get_pixel_color,
    region_has_color, get_pixel_color_from_frame,
)
from game.inventory import InventoryReader
from game.coal_bag import CoalBagManager
from input import mouse
from anti_detect.humanizer import Humanizer
from data.bars import BarType


class FurnaceHandler:
    """
    All furnace-area interactions: conveyor belt, bar dispenser, navigation.
    """

    def __init__(self, regions: ScreenRegions, settings: BotSettings,
                 inventory: InventoryReader, coal_bag: CoalBagManager,
                 humanizer: Humanizer):
        self.regions = regions
        self.settings = settings
        self.inventory = inventory
        self.coal_bag = coal_bag
        self.humanizer = humanizer

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
        Detected by checking if the minimap player dot stays stable.
        """
        start = time.time()
        last_pos = self._get_player_minimap_pos()

        while time.time() - start < timeout:
            time.sleep(0.3)
            current_pos = self._get_player_minimap_pos()

            if current_pos is not None and last_pos is not None:
                dx = abs(current_pos[0] - last_pos[0])
                dy = abs(current_pos[1] - last_pos[1])
                if dx < 3 and dy < 3:
                    # Player hasn't moved significantly — likely arrived
                    self.humanizer.action_delay()
                    return True

            last_pos = current_pos

        return False

    def _get_player_minimap_pos(self):
        """Get approximate player position on the minimap."""
        # The player dot is always at the center of the minimap
        return (self.regions.minimap_cx, self.regions.minimap_cy)

    # ── Conveyor belt ──

    def click_conveyor(self):
        """
        Click the conveyor belt to deposit ores.
        The conveyor has a 'Put-ore-on' left-click option.
        """
        cx, cy = self.regions.conveyor_pos
        mouse.click(cx, cy, variance=4)
        self.humanizer.reaction_delay()

    def deposit_on_conveyor(self, bar_type: BarType):
        """
        Full conveyor deposit sequence:
        1. Click conveyor to deposit inventory ores
        2. If coal bag has coal, empty it
        3. If coal bag coal went to inventory, click conveyor again

        Returns True when inventory is clear of ores.
        """
        coal_bag_slot = self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None

        # Step 1: Click conveyor to deposit what's in inventory
        self.click_conveyor()
        self._wait_for_deposit(timeout=3.0)

        # Step 2: Empty coal bag if it has coal
        if self.settings.use_coal_bag and not self.coal_bag.is_empty:
            self.coal_bag.empty()
            self.humanizer.action_delay()

            # Coal from bag goes to inventory, so click conveyor again
            # to deposit the coal that was in the bag
            if not self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                self.click_conveyor()
                self._wait_for_deposit(timeout=3.0)

        # Verify inventory is clear
        return self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot)

    def _wait_for_deposit(self, timeout=3.0):
        """Wait for the conveyor deposit animation to complete."""
        start = time.time()
        coal_bag_slot = self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None

        while time.time() - start < timeout:
            if self.inventory.is_inventory_empty(exclude_slot=coal_bag_slot):
                return True
            time.sleep(0.3)

        return False

    # ── Bar dispenser ──

    def are_bars_ready(self):
        """
        Check if bars are ready to collect at the dispenser.

        Detection method: The bar dispenser changes appearance when bars
        are ready — it has a visible glow or the bars are visible on it.
        We check the pixel colors at the dispenser position.
        """
        dx, dy = self.regions.dispenser_pos
        # Sample a small area around the dispenser
        frame = capture_region(dx - 20, dy - 20, 40, 40)
        offset = (dx - 20, dy - 20)

        # Check for the characteristic bar-ready glow
        return region_has_color(
            frame, Colors.BAR_READY_GLOW,
            dx - 15, dy - 15, dx + 15, dy + 15,
            tolerance=30, min_pixels=8, region_offset=offset
        )

    def click_dispenser(self):
        """Click the bar dispenser to open the collection widget."""
        dx, dy = self.regions.dispenser_pos
        mouse.click(dx, dy, variance=4)
        self.humanizer.reaction_delay()

    def is_collection_widget_open(self):
        """
        Check if the bar collection widget is visible.
        The widget has a distinctive background color.
        """
        # The widget appears in the center of the game viewport
        wx = self.regions.game_x + self.regions.game_w // 2
        wy = self.regions.game_y + self.regions.game_h // 2
        color = get_pixel_color(wx, wy)
        return color_matches(color, Colors.DISPENSER_WIDGET_BG, COLOR_TOLERANCE)

    def collect_bars(self, bar_type: BarType):
        """
        Full bar collection sequence:
        1. Click the dispenser
        2. Wait for collection widget to open
        3. Click the bar icon to collect all bars
        4. Verify bars are in inventory

        Returns number of bars collected (0 if failed).
        """
        coal_bag_slot = self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None

        # Count items before collection
        items_before = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)

        # Click dispenser
        self.click_dispenser()

        # Wait for widget
        widget_opened = False
        for _ in range(10):
            if self.is_collection_widget_open():
                widget_opened = True
                break
            time.sleep(0.2)

        if not widget_opened:
            return 0

        self.humanizer.action_delay()

        # Click the bar collection button
        bx, by = self.regions.bar_collect_btn
        mouse.click(bx, by, variance=3)
        self.humanizer.reaction_delay()

        # Wait for bars to appear in inventory
        time.sleep(0.5)
        items_after = self.inventory.count_filled_slots(exclude_slot=coal_bag_slot)

        return max(0, items_after - items_before)

    def wait_for_bars(self, timeout=5.0):
        """
        Wait for bars to finish smelting at the dispenser.
        Polls the dispenser state periodically.

        Returns True if bars appear ready within timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.are_bars_ready():
                self.humanizer.action_delay()
                return True
            time.sleep(0.4)
        return False

    # ── Glove management ──

    def swap_to_ice_gloves(self):
        """
        Swap to ice gloves before collecting bars.
        Click ice gloves in inventory to equip them.
        """
        if not self.settings.use_ice_gloves:
            return

        # Ice gloves have a blue-white color
        ice_glove_color = (150, 180, 220)
        coal_bag_slot = self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None

        slot = self.inventory.find_first_slot_with_color(
            ice_glove_color, tolerance=35, exclude_slot=coal_bag_slot
        )
        if slot is not None:
            self.inventory.click_slot(slot)
            self.humanizer.action_delay()

    def swap_to_goldsmith_gauntlets(self):
        """
        Swap to goldsmith gauntlets before depositing gold ore.
        """
        if not self.settings.use_goldsmith_gauntlets:
            return

        # Goldsmith gauntlets have a golden/yellow color
        gauntlet_color = (180, 150, 50)
        coal_bag_slot = self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None

        slot = self.inventory.find_first_slot_with_color(
            gauntlet_color, tolerance=35, exclude_slot=coal_bag_slot
        )
        if slot is not None:
            self.inventory.click_slot(slot)
            self.humanizer.action_delay()

    # ── Area detection ──

    def is_near_bank(self):
        """
        Check if player is near the bank by checking if the bank chest
        is visible/clickable at the expected screen position.
        """
        bx, by = self.regions.bank_pos
        color = get_pixel_color(bx, by)
        # Bank chest has a specific brown/wooden color
        return not color_matches(color, (0, 0, 0), 20)  # Not black/offscreen

    def is_near_conveyor(self):
        """Check if player is near the conveyor belt."""
        cx, cy = self.regions.conveyor_pos
        color = get_pixel_color(cx, cy)
        return not color_matches(color, (0, 0, 0), 20)

    def is_near_dispenser(self):
        """Check if player is near the bar dispenser."""
        dx, dy = self.regions.dispenser_pos
        color = get_pixel_color(dx, dy)
        return not color_matches(color, (0, 0, 0), 20)
