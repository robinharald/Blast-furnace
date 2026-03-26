"""
Run energy monitoring and tea/stamina decisions.
"""
import logging

from config import colors
from screen.capture import get_pixel_color, color_matches
from config.settings import ScreenRegions

logger = logging.getLogger(__name__)


class RunEnergyMonitor:
    """Monitor run energy and decide when to accept tea."""

    def __init__(self, regions: ScreenRegions, tea_threshold: int = 30):
        self._run_orb = (regions.run_orb.x, regions.run_orb.y)
        self.tea_threshold = tea_threshold

    def is_energy_low(self) -> bool:
        """Check if run energy is below threshold (should accept tea)."""
        c = get_pixel_color(self._run_orb[0], self._run_orb[1])
        return color_matches(c, colors.RUN_ORB_LOW, colors.RUN_ORB_TOLERANCE)

    def is_energy_high(self) -> bool:
        """Check if run energy is above threshold."""
        c = get_pixel_color(self._run_orb[0], self._run_orb[1])
        return color_matches(c, colors.RUN_ORB_HIGH, colors.RUN_ORB_TOLERANCE)

    def should_accept_tea(self) -> bool:
        """Decide whether to accept the tea from the homeowner."""
        return self.is_energy_low()
