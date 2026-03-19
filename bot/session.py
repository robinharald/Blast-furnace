"""
Session statistics tracking.
"""

import time
from data.bars import BarType, GOLD_GAUNTLETS_XP


class SessionStats:
    """Tracks all session statistics."""

    def __init__(self, bar_type: BarType, use_goldsmith: bool = False):
        self.bar_type = bar_type
        self.use_goldsmith = use_goldsmith
        self.start_time = time.time()
        self.bars_smelted = 0
        self.trips_made = 0
        self.ore_used = 0
        self.coal_used = 0
        self.errors = 0
        self.breaks_taken = 0

    @property
    def xp_per_bar(self):
        if self.bar_type == BarType.GOLD and self.use_goldsmith:
            return GOLD_GAUNTLETS_XP
        return self.bar_type.data.xp_per_bar

    @property
    def xp_gained(self):
        return self.bars_smelted * self.xp_per_bar

    @property
    def elapsed_seconds(self):
        return time.time() - self.start_time

    @property
    def elapsed_formatted(self):
        elapsed = int(self.elapsed_seconds)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    @property
    def bars_per_hour(self):
        if self.elapsed_seconds < 1:
            return 0
        return int(self.bars_smelted * 3600 / self.elapsed_seconds)

    @property
    def xp_per_hour(self):
        if self.elapsed_seconds < 1:
            return 0
        return int(self.xp_gained * 3600 / self.elapsed_seconds)

    def add_bars(self, count):
        self.bars_smelted += count

    def add_trip(self):
        self.trips_made += 1

    def add_ore(self, count):
        self.ore_used += count

    def add_coal(self, count):
        self.coal_used += count

    def add_error(self):
        self.errors += 1

    def summary(self):
        return (
            f"\n{'=' * 40}\n"
            f"  Blast Furnace Session Summary\n"
            f"{'=' * 40}\n"
            f"  Bar type:    {self.bar_type.data.name}\n"
            f"  Runtime:     {self.elapsed_formatted}\n"
            f"  Bars:        {self.bars_smelted:,} ({self.bars_per_hour:,}/hr)\n"
            f"  XP:          {int(self.xp_gained):,} ({self.xp_per_hour:,}/hr)\n"
            f"  Trips:       {self.trips_made:,}\n"
            f"  Ore used:    {self.ore_used:,}\n"
            f"  Coal used:   {self.coal_used:,}\n"
            f"  Errors:      {self.errors}\n"
            f"  Breaks:      {self.breaks_taken}\n"
            f"{'=' * 40}\n"
        )

    def status_line(self):
        return (
            f"[{self.elapsed_formatted}] "
            f"Bars: {self.bars_smelted:,} ({self.bars_per_hour:,}/hr) | "
            f"XP: {int(self.xp_gained):,} ({self.xp_per_hour:,}/hr) | "
            f"Trips: {self.trips_made}"
        )
