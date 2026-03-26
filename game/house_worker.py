"""
Hotspot interaction — build, repair, and remove furniture.

The core work loop inside a house:
1. Scan for highlighted hotspots
2. Click one
3. Wait for build animation
4. Repeat until none remain
5. Handle floor changes if needed
"""
import time
import random
import logging
from typing import Optional, Tuple, List

from game.object_finder import ObjectFinder
from game.camera import CameraManager
from anti_detect.humanizer import Humanizer
from anti_detect.attention_sim import AttentionSimulator
from screen.capture import find_all_color_clusters, region_has_color
from config import colors
from input import mouse

logger = logging.getLogger(__name__)


class HouseWorker:
    """Interact with hotspots inside a Mahogany Homes house."""

    def __init__(
        self,
        finder: ObjectFinder,
        camera: CameraManager,
        humanizer: Humanizer,
        attention: AttentionSimulator,
        viewport: Tuple[int, int, int, int],
    ):
        self.finder = finder
        self.camera = camera
        self.humanizer = humanizer
        self.attention = attention
        self.vx, self.vy, self.vw, self.vh = viewport
        self._last_click_pos = None

    def find_hotspots(self) -> List[Tuple[int, int]]:
        """Find all highlighted hotspots in the current viewport."""
        return self.finder.find_all_hotspots()

    def find_hotspots_with_camera(self) -> List[Tuple[int, int]]:
        """
        Find hotspots, rotating camera if none visible.
        Tries up to 4 rotations (full 360).
        """
        spots = self.find_hotspots()
        if spots:
            return spots

        logger.debug("No hotspots visible — rotating camera to search")
        result = self.camera.rotate_to_find(self.find_hotspots, max_rotations=4)
        return result if result else []

    def interact_with_hotspot(self, pos: Tuple[int, int]) -> bool:
        """
        Click a highlighted hotspot to build/repair/remove it.
        Handles deliberate imperfection (misclicks, hesitation).
        Returns True if clicked successfully.
        """
        # Maybe hesitate before acting
        self.attention.maybe_hesitate()

        # Maybe misclick (attention sim handles the correction)
        if not self.attention.maybe_misclick(pos[0], pos[1]):
            mouse.click(pos[0], pos[1], variance=4,
                        style=self.attention.profile.pick_mouse_style())

        self._last_click_pos = pos
        self.humanizer.action_delay()
        return True

    def wait_for_build(self, timeout: float = 6.0) -> bool:
        """
        Wait for build/repair animation to complete.
        Detects completion by checking if the hotspot highlight disappeared
        at the last click position.
        """
        if self._last_click_pos is None:
            self.humanizer.build_wait()
            return True

        lx, ly = self._last_click_pos
        check_size = 30
        cx = max(self.vx, lx - check_size // 2)
        cy = max(self.vy, ly - check_size // 2)

        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.4)
            # Check if hotspot highlight is still there
            still_highlighted = region_has_color(
                cx, cy, check_size, check_size,
                colors.HOTSPOT_HIGHLIGHT, colors.HOTSPOT_TOLERANCE,
                min_pixels=8,
            )
            if not still_highlighted:
                logger.debug("Hotspot highlight disappeared — build complete")
                return True

        logger.debug("Build wait timed out — assuming complete")
        return True

    def work_all_hotspots(self) -> int:
        """
        Work all hotspots on the current floor.
        Returns the number of hotspots completed.
        """
        completed = 0

        for attempt in range(20):  # Safety limit
            spots = self.find_hotspots()
            if not spots:
                logger.debug("No more hotspots on current floor")
                break

            # Pick which hotspot to work (with possible imperfection)
            target = self.attention.pick_hotspot(spots)
            if target is None:
                break

            logger.info(f"Working hotspot {completed + 1} at {target} ({len(spots)} remaining)")

            # Click and wait for build
            self.interact_with_hotspot(target)
            self.wait_for_build()
            completed += 1

            # Brief delay between hotspots
            self.humanizer.action_delay()

            # Occasional micro-break between hotspots
            self.humanizer.check_micro_break()

        return completed

    def count_remaining(self) -> int:
        """Count how many highlighted hotspots are still visible."""
        return len(self.find_hotspots())
