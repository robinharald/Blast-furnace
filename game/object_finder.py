"""
Multi-cluster color detection for RuneLite-highlighted game objects.

Detects hotspots, doors, staircases, bank chests, NPCs, and contractors
by scanning the viewport for their assigned RuneLite overlay colors.
"""
import logging
from typing import Optional, Tuple, List

from config import colors
from screen.capture import find_color_in_region, find_all_color_clusters

logger = logging.getLogger(__name__)


class ObjectFinder:
    """
    Find RuneLite-highlighted objects in the game viewport.

    Uses quick-scan (small area around last known position) then
    falls back to full viewport scan if needed.
    """

    def __init__(self, viewport_region: Tuple[int, int, int, int]):
        self.vx, self.vy, self.vw, self.vh = viewport_region
        self._cache = {}  # color -> (x, y) last known position

    def _quick_scan(self, color: tuple, tolerance: float,
                    last_pos: Tuple[int, int], scan_size: int = 120) -> Optional[Tuple[int, int]]:
        """Scan a small area around the last known position."""
        qx = max(self.vx, last_pos[0] - scan_size // 2)
        qy = max(self.vy, last_pos[1] - scan_size // 2)
        qw = min(scan_size, self.vx + self.vw - qx)
        qh = min(scan_size, self.vy + self.vh - qy)
        return find_color_in_region(qx, qy, qw, qh, color, tolerance)

    def find_color(self, color: tuple, tolerance: float = 30,
                   min_pixels: int = 10) -> Optional[Tuple[int, int]]:
        """
        Find the centroid of an object by its overlay color.
        Uses quick scan (cached position) then full viewport scan.
        Returns absolute (x, y) or None.
        """
        color_key = color

        # Try quick scan at cached position
        if color_key in self._cache:
            result = self._quick_scan(color, tolerance, self._cache[color_key])
            if result:
                self._cache[color_key] = result
                return result

        # Full viewport scan
        result = find_color_in_region(
            self.vx, self.vy, self.vw, self.vh,
            color, tolerance, min_pixels,
        )
        if result:
            self._cache[color_key] = result
        return result

    # ------------------------------------------------------------------
    # Specific object finders
    # ------------------------------------------------------------------

    def find_all_hotspots(self) -> List[Tuple[int, int]]:
        """
        Find all highlighted hotspot clusters in the viewport.
        Returns list of (x, y) centroids sorted by distance from center.
        """
        return find_all_color_clusters(
            self.vx, self.vy, self.vw, self.vh,
            colors.HOTSPOT_HIGHLIGHT, colors.HOTSPOT_TOLERANCE,
            min_cluster_pixels=15, max_clusters=10,
        )

    def find_nearest_hotspot(self) -> Optional[Tuple[int, int]]:
        """Find the single nearest highlighted hotspot."""
        spots = self.find_all_hotspots()
        return spots[0] if spots else None

    def find_door(self) -> Optional[Tuple[int, int]]:
        """Find a house door (orange Object Marker)."""
        return self.find_color(colors.DOOR_MARKER, colors.DOOR_TOLERANCE)

    def find_staircase(self) -> Optional[Tuple[int, int]]:
        """Find a staircase (yellow Object Marker)."""
        return self.find_color(colors.STAIRCASE_MARKER, colors.STAIRCASE_TOLERANCE)

    def find_bank(self) -> Optional[Tuple[int, int]]:
        """Find a bank chest (blue Object Marker)."""
        return self.find_color(colors.BANK_MARKER, colors.BANK_TOLERANCE)

    def find_homeowner_npc(self) -> Optional[Tuple[int, int]]:
        """Find the homeowner NPC (magenta NPC Indicator)."""
        return self.find_color(colors.NPC_MARKER, colors.NPC_TOLERANCE)

    def find_contractor_npc(self) -> Optional[Tuple[int, int]]:
        """Find a contractor NPC (lime NPC Indicator, Mode B only)."""
        return self.find_color(colors.CONTRACTOR_MARKER, colors.CONTRACTOR_TOLERANCE)

    def clear_cache(self) -> None:
        """Clear position cache (e.g., after teleporting to a new area)."""
        self._cache.clear()
