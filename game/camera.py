"""
Camera rotation management for finding off-screen hotspots.

Uses arrow keys to rotate the camera. Each 90-degree rotation takes
approximately 0.35-0.45 seconds of holding an arrow key.
"""
import random
import logging
from typing import Optional, Tuple, List

from input.keyboard import hold_key

logger = logging.getLogger(__name__)

# Calibrated hold duration for ~90 degree rotation (adjust if needed)
ROTATION_HOLD_MIN = 0.33
ROTATION_HOLD_MAX = 0.47


class CameraManager:
    """Rotate camera to find off-screen objects."""

    def __init__(self):
        self._rotations_since_reset = 0

    def rotate_90(self, direction: str = "right") -> None:
        """Rotate camera approximately 90 degrees."""
        duration = random.uniform(ROTATION_HOLD_MIN, ROTATION_HOLD_MAX)
        hold_key(direction, duration)
        self._rotations_since_reset += 1
        logger.debug(f"Camera rotated {direction} (~90 deg)")

    def rotate_to_find(self, finder_func, max_rotations: int = 4) -> Optional[any]:
        """
        Rotate camera incrementally until finder_func returns a result.

        Args:
            finder_func: Callable that returns a truthy value when target found
            max_rotations: Maximum 90-degree rotations to try (4 = full 360)

        Returns:
            Result of finder_func, or None if not found after full rotation.
        """
        for i in range(max_rotations):
            result = finder_func()
            if result:
                logger.debug(f"Found target after {i} rotations")
                return result

            direction = random.choice(["left", "right"])
            self.rotate_90(direction)
            # Brief wait for the scene to render after rotation
            import time
            time.sleep(random.uniform(0.3, 0.5))

        # Final check after last rotation
        return finder_func()

    def rotate_random_idle(self) -> None:
        """Small random camera movement (attention simulation)."""
        direction = random.choice(["left", "right"])
        duration = random.uniform(0.08, 0.25)
        hold_key(direction, duration)

    def reset_rotation_count(self) -> None:
        self._rotations_since_reset = 0
