"""
Minimap interaction — click navigation and run energy.

Click on the minimap to walk in a direction. The minimap covers
approximately a 20-tile radius around the player.
"""
import math
import random
import logging
from typing import Tuple

from config.settings import ScreenRegions, Point
from config import colors
from screen.capture import get_pixel_color, color_matches
from input import mouse

logger = logging.getLogger(__name__)

# Minimap radius in pixels (approximate for standard OSRS client)
MINIMAP_RADIUS = 73

# Compass bearing to (dx, dy) multiplier on minimap
BEARING_VECTORS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
    "north-east": (0.7, -0.7),
    "north-west": (-0.7, -0.7),
    "south-east": (0.7, 0.7),
    "south-west": (-0.7, 0.7),
}

# Walk distance multipliers (fraction of minimap radius)
DISTANCE_MULTIPLIERS = {
    "short": 0.4,
    "medium": 0.65,
    "long": 0.85,
}


class MinimapNavigator:
    """Click on the minimap to walk to locations."""

    def __init__(self, regions: ScreenRegions):
        self.regions = regions
        self._center = (regions.minimap_center.x, regions.minimap_center.y)
        self._run_orb = (regions.run_orb.x, regions.run_orb.y)

    def click_direction(self, bearing: str, distance: str = "medium") -> None:
        """
        Click on the minimap in a compass direction at a given distance.

        Args:
            bearing: Compass direction (e.g., "north", "south-east")
            distance: "short", "medium", "long"
        """
        dx, dy = BEARING_VECTORS.get(bearing, (0, -1))
        mult = DISTANCE_MULTIPLIERS.get(distance, 0.65)

        # Add slight randomness to avoid identical clicks
        angle_jitter = random.uniform(-0.1, 0.1)
        dist_jitter = random.uniform(-0.05, 0.05)
        actual_mult = mult + dist_jitter

        # Rotate the vector slightly
        cos_j = math.cos(angle_jitter)
        sin_j = math.sin(angle_jitter)
        jdx = dx * cos_j - dy * sin_j
        jdy = dx * sin_j + dy * cos_j

        target_x = int(self._center[0] + jdx * MINIMAP_RADIUS * actual_mult)
        target_y = int(self._center[1] + jdy * MINIMAP_RADIUS * actual_mult)

        logger.debug(f"Minimap click: {bearing} {distance} -> ({target_x}, {target_y})")
        mouse.click(target_x, target_y, variance=3)

    def click_minimap_point(self, offset_x: int, offset_y: int) -> None:
        """Click at an arbitrary offset from minimap center."""
        tx = self._center[0] + offset_x
        ty = self._center[1] + offset_y
        mouse.click(tx, ty, variance=3)

    def is_run_enabled(self) -> bool:
        """Check if run is toggled on (run orb appears bright)."""
        c = get_pixel_color(self._run_orb[0], self._run_orb[1])
        return color_matches(c, colors.RUN_ORB_HIGH, colors.RUN_ORB_TOLERANCE)

    def is_run_energy_low(self) -> bool:
        """Check if run energy is critically low."""
        c = get_pixel_color(self._run_orb[0], self._run_orb[1])
        return color_matches(c, colors.RUN_ORB_LOW, colors.RUN_ORB_TOLERANCE)

    def toggle_run(self) -> None:
        """Click the run orb to toggle run on/off."""
        mouse.click(self._run_orb[0], self._run_orb[1], variance=3)

    def ensure_running(self) -> None:
        """Make sure run is toggled on."""
        if not self.is_run_enabled():
            self.toggle_run()
