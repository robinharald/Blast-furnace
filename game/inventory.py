"""
Inventory reading and management via pixel/color detection.

Reads inventory slot states by sampling pixel colors at known positions.
No injection — purely visual.

Slots are 1-based (1-28) matching the in-game numbering.
"""

import time
from config import ScreenRegions, Colors, COLOR_TOLERANCE
from screen.capture import capture_region, color_matches, get_pixel_color_from_frame
from input import mouse
from anti_detect.humanizer import Humanizer

# Inventory constants
FIRST_SLOT = 1
LAST_SLOT = 28
TOTAL_SLOTS = 28


class InventoryReader:
    """
    Reads inventory state by analyzing pixel colors in each slot.
    All slot references are 1-based (1-28).
    """

    def __init__(self, regions: ScreenRegions, humanizer: Humanizer):
        self.regions = regions
        self.humanizer = humanizer

    def _capture_inventory(self):
        """Capture the inventory grid area."""
        x = self.regions.inv_x - 5
        y = self.regions.inv_y - 5
        w = self.regions.inv_cols * self.regions.inv_slot_w + 10
        h = self.regions.inv_rows * self.regions.inv_slot_h + 10
        return capture_region(x, y, w, h), (x, y)

    def is_slot_empty(self, slot, frame=None, offset=(0, 0)):
        """Check if an inventory slot appears empty. Slot is 1-based."""
        cx, cy = self.regions.inv_slot_center(slot)

        if frame is not None:
            color = get_pixel_color_from_frame(frame, cx, cy, offset)
        else:
            from screen.capture import get_pixel_color
            color = get_pixel_color(cx, cy)

        return color_matches(color, Colors.INV_EMPTY_SLOT, COLOR_TOLERANCE)

    def is_slot_filled(self, slot, frame=None, offset=(0, 0)):
        """Check if an inventory slot has an item. Slot is 1-based."""
        return not self.is_slot_empty(slot, frame, offset)

    def slot_has_color(self, slot, target_color, tolerance=20, frame=None, offset=(0, 0)):
        """Check if a slot contains an item matching the target color. Slot is 1-based."""
        cx, cy = self.regions.inv_slot_center(slot)

        if frame is not None:
            color = get_pixel_color_from_frame(frame, cx, cy, offset)
        else:
            from screen.capture import get_pixel_color
            color = get_pixel_color(cx, cy)

        return color_matches(color, target_color, tolerance)

    def count_filled_slots(self, exclude_slot=None):
        """Count how many inventory slots have items. Slots 1-28."""
        frame, offset = self._capture_inventory()
        count = 0
        for slot in range(FIRST_SLOT, LAST_SLOT + 1):
            if slot == exclude_slot:
                continue
            if self.is_slot_filled(slot, frame, offset):
                count += 1
        return count

    def count_slots_with_color(self, target_color, tolerance=25, exclude_slot=None):
        """Count slots containing items matching a specific color."""
        frame, offset = self._capture_inventory()
        count = 0
        for slot in range(FIRST_SLOT, LAST_SLOT + 1):
            if slot == exclude_slot:
                continue
            if self.slot_has_color(slot, target_color, tolerance, frame, offset):
                count += 1
        return count

    def find_first_slot_with_color(self, target_color, tolerance=25, exclude_slot=None):
        """Find the first slot containing an item of the given color. Returns 1-based slot."""
        frame, offset = self._capture_inventory()
        for slot in range(FIRST_SLOT, LAST_SLOT + 1):
            if slot == exclude_slot:
                continue
            if self.slot_has_color(slot, target_color, tolerance, frame, offset):
                return slot
        return None

    def is_inventory_empty(self, exclude_slot=None):
        """Check if inventory is empty (excluding locked slot)."""
        return self.count_filled_slots(exclude_slot=exclude_slot) == 0

    def is_inventory_full(self, exclude_slot=None):
        """Check if inventory is full (27 items + 1 locked slot)."""
        return self.count_filled_slots(exclude_slot=exclude_slot) >= 27

    def click_slot(self, slot, action="left"):
        """Click an inventory slot with humanized movement. Slot is 1-based."""
        x, y = self.regions.inv_slot_center(slot)
        x, y = self.humanizer.jitter_position(x, y, radius=4)
        if action == "left":
            mouse.click(x, y)
        else:
            mouse.right_click(x, y)
        self.humanizer.action_delay()

    def get_inventory_snapshot(self, exclude_slot=None):
        """
        Get a full snapshot of inventory state.
        Returns list of 28 booleans (True = filled, False = empty).
        Index 0 = slot 1, index 27 = slot 28.
        """
        frame, offset = self._capture_inventory()
        return [
            self.is_slot_filled(slot, frame, offset) if slot != exclude_slot else True
            for slot in range(FIRST_SLOT, LAST_SLOT + 1)
        ]
