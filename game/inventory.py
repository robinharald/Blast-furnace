"""
Inventory reading and management via pixel/color detection.

Reads inventory slot states by sampling pixel colors at known positions.
No injection — purely visual.
"""

import time
from config import ScreenRegions, Colors, COLOR_TOLERANCE
from screen.capture import capture_region, color_matches, get_pixel_color_from_frame
from input import mouse
from anti_detect.humanizer import Humanizer


class InventoryReader:
    """
    Reads inventory state by analyzing pixel colors in each slot.
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
        """Check if an inventory slot appears empty."""
        cx, cy = self.regions.inv_slot_center(slot)

        if frame is not None:
            color = get_pixel_color_from_frame(frame, cx, cy, offset)
        else:
            from screen.capture import get_pixel_color
            color = get_pixel_color(cx, cy)

        return color_matches(color, Colors.INV_EMPTY_SLOT, COLOR_TOLERANCE)

    def is_slot_filled(self, slot, frame=None, offset=(0, 0)):
        """Check if an inventory slot has an item."""
        return not self.is_slot_empty(slot, frame, offset)

    def slot_has_color(self, slot, target_color, tolerance=20, frame=None, offset=(0, 0)):
        """Check if a slot contains an item matching the target color."""
        cx, cy = self.regions.inv_slot_center(slot)

        if frame is not None:
            color = get_pixel_color_from_frame(frame, cx, cy, offset)
        else:
            from screen.capture import get_pixel_color
            color = get_pixel_color(cx, cy)

        return color_matches(color, target_color, tolerance)

    def count_filled_slots(self, exclude_slot=None):
        """Count how many inventory slots have items."""
        frame, offset = self._capture_inventory()
        count = 0
        for slot in range(28):
            if slot == exclude_slot:
                continue
            if self.is_slot_filled(slot, frame, offset):
                count += 1
        return count

    def count_slots_with_color(self, target_color, tolerance=25, exclude_slot=None):
        """Count slots containing items matching a specific color."""
        frame, offset = self._capture_inventory()
        count = 0
        for slot in range(28):
            if slot == exclude_slot:
                continue
            if self.slot_has_color(slot, target_color, tolerance, frame, offset):
                count += 1
        return count

    def find_first_slot_with_color(self, target_color, tolerance=25, exclude_slot=None):
        """Find the first slot containing an item of the given color."""
        frame, offset = self._capture_inventory()
        for slot in range(28):
            if slot == exclude_slot:
                continue
            if self.slot_has_color(slot, target_color, tolerance, frame, offset):
                return slot
        return None

    def is_inventory_empty(self, exclude_slot=None):
        """Check if inventory is empty (excluding coal bag slot)."""
        return self.count_filled_slots(exclude_slot=exclude_slot) == 0

    def is_inventory_full(self, exclude_slot=None):
        """Check if inventory is full."""
        return self.count_filled_slots(exclude_slot=exclude_slot) >= 27

    def click_slot(self, slot, action="left"):
        """Click an inventory slot with humanized movement."""
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
        """
        frame, offset = self._capture_inventory()
        return [
            self.is_slot_filled(i, frame, offset) if i != exclude_slot else True
            for i in range(28)
        ]
