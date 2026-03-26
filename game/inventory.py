"""
Inventory slot reading and item counting.

Reads inventory state by sampling pixel colors at slot centers.
OSRS inventory is a 4x7 grid of 28 slots.
"""
import logging
from typing import Optional, Tuple, List

from config.settings import ScreenRegions
from screen.capture import get_pixel_color, color_matches
from config import colors
from input import mouse

logger = logging.getLogger(__name__)


class InventoryReader:
    """Read and interact with the OSRS inventory."""

    def __init__(self, regions: ScreenRegions):
        self.regions = regions

    def _slot_center(self, slot: int) -> Tuple[int, int]:
        """Get absolute (x, y) center of an inventory slot."""
        return self.regions.inventory_slot_center(slot)

    def get_slot_color(self, slot: int) -> Tuple[int, int, int]:
        """Read the color at the center of an inventory slot."""
        x, y = self._slot_center(slot)
        return get_pixel_color(x, y)

    def is_slot_empty(self, slot: int) -> bool:
        """Check if a slot is empty (matches empty background color)."""
        c = self.get_slot_color(slot)
        return color_matches(c, colors.INV_EMPTY_SLOT, colors.INV_EMPTY_TOLERANCE)

    def is_slot_filled(self, slot: int) -> bool:
        return not self.is_slot_empty(slot)

    def slot_has_color(self, slot: int, target_color: tuple, tolerance: float = 25) -> bool:
        """Check if a slot contains an item of the given color."""
        c = self.get_slot_color(slot)
        return color_matches(c, target_color, tolerance)

    def count_filled_slots(self) -> int:
        """Count total non-empty inventory slots."""
        return sum(1 for s in range(28) if self.is_slot_filled(s))

    def count_slots_with_color(self, target_color: tuple, tolerance: float = 25) -> int:
        """Count inventory slots matching a specific item color."""
        return sum(1 for s in range(28) if self.slot_has_color(s, target_color, tolerance))

    def find_first_slot_with_color(self, target_color: tuple,
                                    tolerance: float = 25) -> Optional[int]:
        """Find the first slot containing an item of the given color."""
        for s in range(28):
            if self.slot_has_color(s, target_color, tolerance):
                return s
        return None

    def find_all_slots_with_color(self, target_color: tuple,
                                   tolerance: float = 25) -> List[int]:
        """Find all slots containing items of a given color."""
        return [s for s in range(28) if self.slot_has_color(s, target_color, tolerance)]

    def click_slot(self, slot: int, variance: float = 3.0,
                   style: Optional[str] = None, button: str = "left") -> None:
        """Click an inventory slot."""
        x, y = self._slot_center(slot)
        if button == "left":
            mouse.click(x, y, variance=variance, style=style)
        else:
            mouse.right_click(x, y, variance=variance, style=style)

    # ------------------------------------------------------------------
    # High-level item counting
    # ------------------------------------------------------------------

    def count_planks(self, plank_color: tuple, tolerance: float = 25) -> int:
        """Count planks in inventory by color."""
        return self.count_slots_with_color(plank_color, tolerance)

    def count_steel_bars(self) -> int:
        """Count steel bars in inventory."""
        return self.count_slots_with_color(colors.STEEL_BAR, colors.STEEL_BAR_TOLERANCE)

    def count_teleport_tabs(self) -> int:
        """Count teleport tabs in inventory."""
        return self.count_slots_with_color(colors.TELEPORT_TAB, colors.TELEPORT_TAB_TOLERANCE)

    def is_inventory_full(self) -> bool:
        """Check if all 28 slots are filled."""
        return self.count_filled_slots() >= 28

    def is_inventory_empty(self) -> bool:
        """Check if no slots are filled (unlikely, but for safety)."""
        return self.count_filled_slots() == 0
