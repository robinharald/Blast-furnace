"""
Timing humanization, fatigue simulation, and break management.

All delays flow through this module to ensure consistent, human-like
behavior that varies with fatigue and session personality.
"""
import random
import time
import logging
from typing import Optional

from anti_detect.session_profile import SessionProfile

logger = logging.getLogger(__name__)


class Humanizer:
    """
    Central timing engine. Every delay in the bot passes through here.

    Features:
    - Multi-phase fatigue model (warm-up -> peak -> decline)
    - Mixture timing distributions (normal + distracted + anticipated)
    - Micro-break injection
    - Macro-break scheduling
    - Session length enforcement
    """

    def __init__(self, profile: SessionProfile):
        self.profile = profile
        self._session_start = time.time()
        self._last_break_time = time.time()
        self._planned_breaks = self._plan_breaks()
        self._action_count = 0

    # ------------------------------------------------------------------
    # Fatigue Model
    # ------------------------------------------------------------------

    def _session_minutes(self) -> float:
        return (time.time() - self._session_start) / 60.0

    def _minutes_since_last_break(self) -> float:
        return (time.time() - self._last_break_time) / 60.0

    def fatigue_factor(self) -> float:
        """
        Multi-phase fatigue model:
        - 0-15 min:  Warming up (1.05x -> 1.0x, slightly slower)
        - 15-60 min: Peak performance (1.0x)
        - 60-90 min: Gradual slowdown (1.0x -> 1.06x)
        - 90+ min:   Noticeable fatigue (1.06x+)
        - After break: Alertness spike (0.95x for 5 min)
        """
        minutes = self._session_minutes()

        if minutes < 15:
            base = 1.05 - 0.003 * minutes
        elif minutes < 60:
            base = 1.0
        elif minutes < 90:
            base = 1.0 + 0.002 * (minutes - 60)
        else:
            base = 1.06 + 0.001 * (minutes - 90)

        # Alertness spike after break
        if self._minutes_since_last_break() < 5:
            base *= 0.95

        return max(0.8, min(1.3, base))

    # ------------------------------------------------------------------
    # Timing Distributions
    # ------------------------------------------------------------------

    def _humanized_delay(self, base_ms: float, variance_ms: Optional[float] = None) -> float:
        """
        Generate a delay from a mixture distribution:
        - 85%: Normal (typical reaction)
        - 10%: Longer pause (distraction)
        - 5%:  Very short (anticipated action)
        """
        if variance_ms is None:
            variance_ms = base_ms * 0.3

        roll = random.random()
        if roll < 0.05:
            # Quick — already knew what to do
            delay = base_ms * random.uniform(0.5, 0.7)
        elif roll < 0.15:
            # Distracted moment
            delay = base_ms + random.uniform(variance_ms, variance_ms * 4)
        else:
            # Normal reaction
            delay = base_ms + random.gauss(0, variance_ms)

        delay *= self.profile.reaction_speed
        delay *= self.fatigue_factor()

        return max(30, delay)

    # ------------------------------------------------------------------
    # Public Delay Methods
    # ------------------------------------------------------------------

    def sleep(self, base_ms: float, variance_ms: Optional[float] = None) -> None:
        """Sleep for a humanized duration."""
        ms = self._humanized_delay(base_ms, variance_ms)
        time.sleep(ms / 1000.0)

    def action_delay(self) -> None:
        """Delay between sequential actions (e.g., click -> click)."""
        self.sleep(180, 80)
        self._action_count += 1

    def reaction_delay(self) -> None:
        """Delay after a visual change (e.g., dialogue appeared)."""
        self.sleep(280, 120)

    def transition_delay(self) -> None:
        """Delay between state transitions."""
        self.sleep(400, 150)

    def walk_delay(self) -> None:
        """Delay after initiating a walk."""
        self.sleep(600, 200)

    def bank_delay(self) -> None:
        """Delay during banking operations."""
        self.sleep(350, 130)

    def tick_delay(self) -> None:
        """Wait approximately one game tick (~600ms)."""
        self.sleep(600, 60)

    def build_wait(self) -> None:
        """Wait for a build animation (~5 ticks = 3000ms)."""
        self.sleep(3000, 300)

    def teleport_wait(self) -> None:
        """Wait for teleport animation to complete."""
        self.sleep(2500, 400)

    # ------------------------------------------------------------------
    # Break Management
    # ------------------------------------------------------------------

    def _plan_breaks(self) -> list:
        """Pre-plan break times with natural variance."""
        breaks = []
        t = random.uniform(15, 30) * 60  # first break 15-30 min in
        session_end = self.profile.session_length_minutes * 60
        while t < session_end:
            duration = random.uniform(*self.profile.macro_break_duration_range)
            breaks.append((t, duration))
            t += random.uniform(15, 45) * 60
        return breaks

    def check_and_take_break(self) -> bool:
        """
        Check if it's time for a planned break. If so, take it.
        Returns True if a break was taken.
        """
        elapsed = time.time() - self._session_start
        for i, (break_time, duration) in enumerate(self._planned_breaks):
            if abs(elapsed - break_time) < 60:  # within 1 minute of planned break
                logger.info(f"Taking planned break for {duration:.0f}s")
                self._planned_breaks.pop(i)
                time.sleep(duration)
                self._last_break_time = time.time()
                return True
        return False

    def check_micro_break(self) -> bool:
        """Possibly take a micro-break (1-5 seconds)."""
        if self.profile.should_micro_break():
            duration = random.uniform(1.0, 5.0) * self.fatigue_factor()
            logger.debug(f"Micro-break: {duration:.1f}s")
            time.sleep(duration)
            return True
        return False

    def should_stop_session(self) -> bool:
        """Check if the session should end based on planned length."""
        return self._session_minutes() >= self.profile.session_length_minutes

    def session_elapsed(self) -> float:
        """Return session elapsed time in seconds."""
        return time.time() - self._session_start
