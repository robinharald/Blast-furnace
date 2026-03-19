"""
Coal bag management with locked inventory slot.

The coal bag occupies a fixed slot and is NEVER deposited or moved.
All banking operations must skip this slot.

Key mechanics (from OSRS wiki):
- Coal bag holds 27 coal (36 with Smithing cape)
- In BANK (interface open): LEFT-CLICK = "Fill" (fills bag from bank coal)
- In INVENTORY (bank closed): LEFT-CLICK = "Empty" (dumps coal to inventory)
- The context (bank open vs closed) determines which action left-click performs
- Quirk: bag holds 27 but inventory carries 27 ore (28 - bag slot),
  so after depositing at conveyor, 1 coal may remain in bag.
  On next bank visit, the left-click while bank is open will still be "Fill"
  if the bag is not completely full. Need to empty residual first, then fill.
"""

import time
from config import ScreenRegions
from game.inventory import InventoryReader
from input import mouse
from anti_detect.humanizer import Humanizer


class CoalBagManager:
    """
    Manages the coal bag: filling from bank, emptying at conveyor.
    Tracks coal count internally since we can't read bag contents visually.
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
        Fill the coal bag while bank is open.

        In the bank interface, left-clicking the coal bag = "Fill".
        However, if the bag has residual coal (1 left from previous cycle),
        the default left-click might show "Empty" instead.
        We handle this by: left-click (empties residual), then left-click again (fills).
        """
        x, y = self.regions.inv_slot_center(self.locked_slot)
        x, y = self.humanizer.jitter_position(x, y, radius=3)

        if self._coal_count > 0 and self._coal_count < self.CAPACITY:
            # Has residual coal — click once to empty it into bank, then fill
            mouse.click(x, y)
            self.humanizer.action_delay()
            # Now click again to fill
            x2, y2 = self.regions.inv_slot_center(self.locked_slot)
            x2, y2 = self.humanizer.jitter_position(x2, y2, radius=3)
            mouse.click(x2, y2)
            self.humanizer.action_delay()
        else:
            # Empty bag — single click to fill
            mouse.click(x, y)
            self.humanizer.action_delay()

        self._coal_count = self.CAPACITY

    def empty_at_conveyor(self):
        """
        Empty the coal bag when NOT in the bank interface.

        When the bank is closed, LEFT-CLICK on the coal bag = "Empty".
        This dumps coal into inventory. Then click conveyor to deposit it.

        Returns True if bag was emptied.
        """
        if self._coal_count <= 0:
            return False

        x, y = self.regions.inv_slot_center(self.locked_slot)
        x, y = self.humanizer.jitter_position(x, y, radius=3)

        # Left-click = "Empty" when bank is not open
        mouse.click(x, y)
        self.humanizer.action_delay()

        # Brief wait for coal to appear in inventory
        time.sleep(0.3)
        self._coal_count = 0
        return True

    def is_bag_present(self):
        """
        Check if the coal bag is still in its locked slot.
        """
        return self.inventory.is_slot_filled(self.locked_slot)

    def get_locked_slot(self):
        """Return the locked slot number."""
        return self.locked_slot

    def reset_count(self):
        """Reset the internal coal counter."""
        self._coal_count = 0

    def set_count(self, count):
        """Manually set coal count (for recovery/sync)."""
        self._coal_count = min(count, self.CAPACITY)
