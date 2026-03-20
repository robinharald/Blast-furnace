"""
Coal bag management with locked inventory slot.

The coal bag occupies a fixed slot and is NEVER deposited or moved.
All banking operations must skip this slot.

Key mechanics (from OSRS wiki):
- Coal bag holds 27 coal (36 with Smithing cape)
- In BANK (interface open): LEFT-CLICK = "Fill" (fills bag from bank coal)
- In INVENTORY (bank closed): LEFT-CLICK = "Empty" (dumps coal to inventory)
- The context (bank open vs closed) determines which action left-click performs
- With deposit-locked slot for coal bag, 27 free slots remain (28 - 1 locked).
  Bag holds 27, empties perfectly with no residual.
- The locked slot is set via OSRS native deposit locks (per-slot).
  "Deposit inventory" automatically skips locked slots.
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

    def empty_at_conveyor(self, free_slots=27):
        """
        Empty the coal bag when NOT in the bank interface.

        When the bank is closed, LEFT-CLICK on the coal bag = "Empty".
        This dumps coal into inventory. Then click conveyor to deposit it.

        Coal bag holds 27. With 1 locked slot (coal bag itself), 27 slots are free.
        All 27 coal empty perfectly — no residual.
        (Gold bars use glove slot instead of coal bag, so this is only for coal bars.)

        Args:
            free_slots: Number of free inventory slots. Defaults to 27
                        (28 total - coal bag slot). Override if inventory isn't empty.

        Returns True if bag was emptied (even partially).
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

        # Track residual: bag had 27 but only 26 slots free → 1 remains
        emptied = min(self._coal_count, free_slots)
        self._coal_count = max(0, self._coal_count - emptied)
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
