"""
Coal bag management with locked inventory slot.

The coal bag occupies a fixed slot and is NEVER deposited or moved.
All banking operations must skip this slot.
"""

import time
from config import ScreenRegions
from game.inventory import InventoryReader
from input import mouse
from anti_detect.humanizer import Humanizer


class CoalBagManager:
    """
    Manages the coal bag: filling from bank, emptying at conveyor.
    Tracks coal count internally since we can't read the bag contents.
    """

    CAPACITY = 27

    def __init__(self, locked_slot: int, regions: ScreenRegions,
                 inventory: InventoryReader, humanizer: Humanizer):
        self.locked_slot = locked_slot
        self.regions = regions
        self.inventory = inventory
        self.humanizer = humanizer
        self._coal_count = 0

    @property
    def coal_count(self):
        return self._coal_count

    @property
    def is_full(self):
        return self._coal_count >= self.CAPACITY

    @property
    def is_empty(self):
        return self._coal_count <= 0

    def fill(self):
        """
        Fill the coal bag. Must be called while the bank is open.
        Right-click the coal bag in inventory -> "Fill"
        or simply left-click it while bank is open (fills automatically).
        """
        x, y = self.regions.inv_slot_center(self.locked_slot)
        x, y = self.humanizer.jitter_position(x, y, radius=3)
        mouse.click(x, y)
        self.humanizer.action_delay()
        self._coal_count = self.CAPACITY

    def empty(self):
        """
        Empty the coal bag at the conveyor belt.
        Left-click the coal bag in inventory to empty it.
        """
        if self._coal_count <= 0:
            return

        x, y = self.regions.inv_slot_center(self.locked_slot)
        x, y = self.humanizer.jitter_position(x, y, radius=3)
        mouse.click(x, y)
        self.humanizer.action_delay()
        # Wait for the coal to appear in inventory / be deposited
        time.sleep(0.3)
        self._coal_count = 0

    def is_bag_present(self):
        """
        Check if the coal bag is still in its locked slot.
        The coal bag has a distinct dark appearance.
        """
        return self.inventory.is_slot_filled(self.locked_slot)

    def get_locked_slot(self):
        """Return the locked slot number."""
        return self.locked_slot

    def reset_count(self):
        """Reset the internal coal counter (e.g., after depositing on conveyor)."""
        self._coal_count = 0

    def set_count(self, count):
        """Manually set coal count (for recovery/sync)."""
        self._coal_count = min(count, self.CAPACITY)
