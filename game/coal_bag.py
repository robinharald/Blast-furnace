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

IMPORTANT: We do NOT trust an internal coal counter. Server lag can cause
clicks to not register, desyncing any counter. Instead we verify every
fill and empty action visually:
  - fill(): Compare bank coal slot pixels before/after clicking.
  - empty_at_conveyor(): Poll inventory for new items appearing.
"""

import time
import numpy as np
from config import ScreenRegions
from screen.capture import capture_region, get_pixel_color
from game.inventory import InventoryReader
from input import mouse
from anti_detect.humanizer import Humanizer


class CoalBagManager:
    """
    Manages the coal bag: filling from bank, emptying at conveyor.
    All actions are visually verified — no internal coal counter.
    """

    CAPACITY = 27
    MAX_FILL_RETRIES = 3
    MAX_EMPTY_RETRIES = 3

    def __init__(self, locked_slot: int, regions: ScreenRegions,
                 inventory: InventoryReader, humanizer: Humanizer):
        self.locked_slot = locked_slot
        self.regions = regions
        self.inventory = inventory
        self.humanizer = humanizer

        # Bank coal slot position (set by caller after bank opens)
        # This is the position of the coal item in the bank search results.
        self._bank_coal_pos = None

    def set_bank_coal_pos(self, x, y):
        """Set the position of the coal item in bank (for quantity change detection)."""
        self._bank_coal_pos = (x, y)

    def _snapshot_bank_coal_area(self):
        """
        Capture a small region around the bank coal item's quantity text.
        The quantity number sits in the top-left corner of the bank slot icon.
        Capturing a ~30x15 area covers the quantity digits.
        """
        if self._bank_coal_pos is None:
            return None
        bx, by = self._bank_coal_pos
        # Quantity text is in the top-left of the item icon
        return capture_region(bx - 15, by - 15, 30, 15)

    def _bank_coal_changed(self, before_snap, after_snap):
        """Check if the bank coal quantity area changed between two snapshots."""
        if before_snap is None or after_snap is None:
            return True  # Can't verify, assume it worked
        if before_snap.shape != after_snap.shape:
            return True
        diff = np.mean(np.abs(before_snap.astype(float) - after_snap.astype(float)))
        # If mean pixel difference > 3, the quantity text changed
        return diff > 3.0

    def fill(self):
        """
        Fill the coal bag while bank is open. Visually verified.

        In the bank interface, left-clicking the coal bag = "Fill".
        This pulls coal from the bank into the bag.

        Verification: snapshot the bank coal item's quantity area before
        and after clicking. If the quantity text pixels changed, the fill
        worked. If not, retry up to MAX_FILL_RETRIES times.

        Returns True if fill was verified, False if all retries failed.
        """
        for attempt in range(self.MAX_FILL_RETRIES):
            # Snapshot bank coal quantity BEFORE
            before = self._snapshot_bank_coal_area()

            # Click coal bag to fill
            x, y = self.regions.inv_slot_center(self.locked_slot)
            x, y = self.humanizer.jitter_position(x, y, radius=3)
            mouse.click(x, y)
            self.humanizer.action_delay()

            # Wait for server to process
            time.sleep(0.3)

            # Snapshot bank coal quantity AFTER
            after = self._snapshot_bank_coal_area()

            # Verify: did the bank coal quantity change?
            if self._bank_coal_changed(before, after):
                return True

            # Click didn't register — retry
            if attempt < self.MAX_FILL_RETRIES - 1:
                self.humanizer.action_delay()

        return False

    def empty_at_conveyor(self):
        """
        Empty the coal bag when NOT in the bank interface. Visually verified.

        When the bank is closed, LEFT-CLICK on the coal bag = "Empty".
        This dumps coal into inventory.

        Verification: count filled inventory slots before and after clicking.
        If slot count increased, coal was emptied. If not, retry.

        Returns True if empty was verified (items appeared in inventory).
        """
        coal_bag_slot = self.locked_slot

        for attempt in range(self.MAX_EMPTY_RETRIES):
            # Count filled slots BEFORE
            filled_before = self.inventory.count_filled_slots(
                exclude_slot=coal_bag_slot
            )

            # Click coal bag to empty
            x, y = self.regions.inv_slot_center(self.locked_slot)
            x, y = self.humanizer.jitter_position(x, y, radius=3)
            mouse.click(x, y)
            self.humanizer.action_delay()

            # Poll for coal appearing in inventory (dynamic wait)
            verified = self._poll_for_inventory_change(
                filled_before, coal_bag_slot, timeout=1.5
            )
            if verified:
                return True

            # Click didn't register — retry
            if attempt < self.MAX_EMPTY_RETRIES - 1:
                self.humanizer.action_delay()

        return False

    def _poll_for_inventory_change(self, count_before, exclude_slot, timeout=1.5):
        """Poll inventory until filled slot count increases or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            count_now = self.inventory.count_filled_slots(exclude_slot=exclude_slot)
            if count_now > count_before:
                return True
            time.sleep(0.15)
        return False

    def is_bag_present(self):
        """Check if the coal bag is still in its locked slot."""
        return self.inventory.is_slot_filled(self.locked_slot)

    def get_locked_slot(self):
        """Return the locked slot number."""
        return self.locked_slot
