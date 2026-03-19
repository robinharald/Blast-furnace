"""
Anti-detection humanization layer.

Simulates human fatigue, attention drift, micro-breaks, and natural
variability in timing. Every single delay in the bot flows through here.

Key principles:
- No two delays are ever the same
- Longer sessions = gradually slower reactions (fatigue)
- Occasional micro-pauses (looking at phone, reading chat, etc.)
- Mouse doesn't always go directly to the next target
- Sometimes we "misclick" slightly and correct
"""

import random
import time
import math

from input import mouse


class Humanizer:
    """
    Manages all timing and behavior humanization for a session.
    """

    def __init__(self):
        self._session_start = time.time()
        self._last_action = time.time()
        self._action_count = 0
        self._fatigue_factor = 1.0

        # Per-session personality — randomized once at start
        self._base_speed = random.uniform(0.85, 1.15)    # Some people are faster
        self._patience = random.uniform(0.8, 1.3)        # Some people wait longer
        self._precision = random.uniform(0.9, 1.1)       # Click accuracy variance
        self._break_frequency = random.uniform(0.002, 0.008)  # How often micro-breaks occur
        self._idle_chance = random.uniform(0.01, 0.04)    # Chance of random idle per action

    def _session_minutes(self):
        return (time.time() - self._session_start) / 60

    def _update_fatigue(self):
        """
        Fatigue increases logarithmically over the session.
        After 30 mins: ~1.05x slower
        After 60 mins: ~1.1x slower
        After 120 mins: ~1.15x slower
        """
        minutes = self._session_minutes()
        self._fatigue_factor = 1.0 + 0.04 * math.log1p(minutes / 10)

    def sleep(self, base_ms, variance_ms=None):
        """
        Sleep for a humanized duration.
        The actual sleep is base_ms +/- variance, modified by fatigue and personality.

        Args:
            base_ms: base delay in milliseconds
            variance_ms: random variance range (defaults to base_ms * 0.3)
        """
        if variance_ms is None:
            variance_ms = base_ms * 0.3

        self._update_fatigue()

        # Calculate actual delay
        delay = base_ms + random.uniform(-variance_ms, variance_ms)
        delay *= self._base_speed
        delay *= self._fatigue_factor

        # Occasional extra pause (checking chat, looking away)
        if random.random() < self._idle_chance:
            delay += random.uniform(300, 1200)

        delay = max(30, delay)  # Never less than 30ms
        time.sleep(delay / 1000.0)

        self._last_action = time.time()
        self._action_count += 1

    def action_delay(self):
        """Short delay between sequential actions (e.g., click then check)."""
        self.sleep(180, 80)

    def reaction_delay(self):
        """Delay simulating human reaction to a visual change."""
        self.sleep(280, 120)

    def transition_delay(self):
        """Delay between state transitions (e.g., bank closes -> walk)."""
        self.sleep(400, 150)

    def walk_delay(self):
        """Delay after initiating a walk (before checking arrival)."""
        self.sleep(600, 200)

    def bank_delay(self):
        """Delay during banking operations (reading bank contents)."""
        self.sleep(350, 130)

    def tick_delay(self):
        """Wait approximately one game tick (600ms) with human variance."""
        self.sleep(600, 60)

    def maybe_micro_break(self):
        """
        Occasionally take a short break (1-5 seconds).
        Simulates player glancing away from screen.
        Returns True if a break was taken.
        """
        if random.random() < self._break_frequency:
            duration = random.uniform(1.0, 5.0)
            # Longer breaks later in the session
            duration *= self._fatigue_factor
            time.sleep(duration)
            return True
        return False

    def maybe_mouse_drift(self):
        """
        Occasionally move the mouse to a random neutral position.
        Simulates idle hand movement.
        """
        if random.random() < 0.03:
            mouse.move_off_target()
            self.sleep(200, 100)

    def should_take_break(self):
        """
        Check if we should take a longer break (30s-2min).
        This happens roughly every 15-30 minutes.
        """
        minutes = self._session_minutes()
        # After initial period, periodic breaks
        if minutes < 15:
            return False
        # Rough check every loop
        if random.random() < 0.0002:  # ~once per 15-25 min at typical loop speed
            return True
        return False

    def take_long_break(self):
        """Take a longer idle break (30-120 seconds)."""
        duration = random.uniform(30, 120)
        mouse.move_off_target()
        time.sleep(duration)

    def jitter_position(self, x, y, radius=3):
        """
        Add gaussian jitter to a click position.
        Humans don't click the exact same pixel twice.
        """
        jx = int(random.gauss(x, radius * self._precision))
        jy = int(random.gauss(y, radius * self._precision))
        return (jx, jy)

    def get_stats(self):
        """Return humanizer stats for debugging."""
        return {
            "session_minutes": round(self._session_minutes(), 1),
            "actions": self._action_count,
            "fatigue": round(self._fatigue_factor, 3),
            "speed_personality": round(self._base_speed, 2),
        }
