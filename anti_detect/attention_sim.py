"""
Simulates human attention patterns and deliberate imperfection.

A real player doesn't robotically complete contracts nonstop. They:
- Check their stats
- Idle the camera
- Hover over items
- Accidentally right-click
- Hesitate before acting
- Misclick occasionally

This module probabilistically triggers these behaviors.
"""
import random
import time
import logging

from anti_detect.session_profile import SessionProfile
from input import mouse, keyboard

logger = logging.getLogger(__name__)


class AttentionSimulator:
    """Simulates human attention and imperfection behaviors."""

    def __init__(self, profile: SessionProfile, regions=None):
        self.profile = profile
        self.regions = regions  # ScreenRegions, set after calibration

    def maybe_do_human_thing(self) -> bool:
        """
        Probabilistically execute a human-like non-task action.
        Called between contracts or during natural pauses.
        Returns True if an action was taken.
        """
        if not self.profile.should_distract():
            return False

        roll = random.random()

        if roll < 0.25 and self.profile.checks_stats:
            self._check_skills_tab()
        elif roll < 0.45:
            self._idle_camera_movement()
        elif roll < 0.60:
            self._hover_random_item()
        elif roll < 0.72:
            self._move_mouse_off_screen()
        elif roll < 0.82:
            self._accidental_right_click()
        elif roll < 0.90 and self.profile.checks_equipment:
            self._check_equipment_tab()
        else:
            # Just pause briefly (looking at something)
            time.sleep(random.uniform(0.5, 2.0))

        return True

    def _check_skills_tab(self) -> None:
        """Open skills tab, hover over construction, close."""
        logger.debug("Attention: checking skills tab")
        keyboard.press_f_key(2)  # Skills tab
        time.sleep(random.uniform(1.0, 2.5))
        # Hover somewhere in the skills area
        if self.regions:
            sx, sy = self.regions.viewport.center
            mouse.move_to(sx + random.randint(-50, 50), sy + random.randint(-30, 30),
                          variance=5, style="lazy")
        time.sleep(random.uniform(1.5, 3.0))
        keyboard.press_f_key(3)  # Back to inventory

    def _check_equipment_tab(self) -> None:
        """Open equipment tab briefly."""
        logger.debug("Attention: checking equipment tab")
        if self.regions:
            mouse.click(self.regions.equipment_tab.x, self.regions.equipment_tab.y,
                         variance=4, style="lazy")
        time.sleep(random.uniform(1.0, 2.5))
        keyboard.press_f_key(3)  # Back to inventory

    def _idle_camera_movement(self) -> None:
        """Small random camera rotation."""
        logger.debug("Attention: idle camera pan")
        direction = random.choice(["left", "right"])
        duration = random.uniform(0.1, 0.4)
        keyboard.hold_key(direction, duration)

    def _hover_random_item(self) -> None:
        """Hover over a random inventory item (reading tooltip)."""
        logger.debug("Attention: hovering random item")
        if self.regions:
            slot = random.randint(0, 27)
            sx, sy = self.regions.inventory_slot_center(slot)
            mouse.move_to(sx, sy, variance=4, style="lazy")
            time.sleep(random.uniform(0.5, 1.5))

    def _move_mouse_off_screen(self) -> None:
        """Move mouse to edge of game area briefly."""
        logger.debug("Attention: mouse drift off-screen")
        if self.regions:
            edge_x = self.regions.viewport.x + self.regions.viewport.w - random.randint(5, 30)
            edge_y = self.regions.viewport.y + random.randint(50, 200)
            mouse.move_to(edge_x, edge_y, variance=10, style="lazy")
            time.sleep(random.uniform(0.8, 2.5))

    def _accidental_right_click(self) -> None:
        """Right-click near current position, then dismiss with ESC."""
        logger.debug("Attention: accidental right-click")
        import pyautogui
        cx, cy = pyautogui.position()
        mouse.right_click(cx + random.randint(-20, 20), cy + random.randint(-20, 20),
                           variance=2)
        time.sleep(random.uniform(0.3, 0.8))
        keyboard.press_escape()

    # ------------------------------------------------------------------
    # Deliberate Imperfection (called by game modules)
    # ------------------------------------------------------------------

    def maybe_misclick(self, target_x: int, target_y: int) -> bool:
        """
        5% chance of clicking off-target, pausing, then correcting.
        Returns True if a misclick occurred (caller should not click again).
        """
        if not self.profile.should_misclick():
            return False

        logger.debug("Imperfection: misclick")
        off_x = target_x + random.choice([-1, 1]) * random.randint(15, 40)
        off_y = target_y + random.choice([-1, 1]) * random.randint(15, 40)
        mouse.click(off_x, off_y, variance=2)
        time.sleep(random.uniform(0.3, 0.8))  # "realize mistake"
        mouse.click(target_x, target_y, variance=3)  # correct
        return True

    def maybe_hesitate(self) -> bool:
        """Pause before acting, as if thinking."""
        if not self.profile.should_hesitate():
            return False
        duration = random.uniform(0.4, 2.0)
        logger.debug(f"Imperfection: hesitating {duration:.1f}s")
        time.sleep(duration)
        return True

    def pick_hotspot(self, hotspots: list) -> tuple:
        """
        Pick which hotspot to interact with next.
        Usually nearest, but sometimes picks 2nd or 3rd nearest.
        """
        if len(hotspots) <= 1:
            return hotspots[0] if hotspots else None

        if self.profile.should_suboptimal_order():
            idx = random.randint(1, min(2, len(hotspots) - 1))
            logger.debug(f"Imperfection: picked hotspot #{idx} instead of nearest")
            return hotspots[idx]

        return hotspots[0]
