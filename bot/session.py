"""
Session statistics tracking.
"""
import time
from dataclasses import dataclass, field


@dataclass
class SessionStats:
    """Track bot performance during a session."""
    contracts_completed: int = 0
    total_points: int = 0
    total_xp: int = 0
    planks_used: int = 0
    steel_bars_used: int = 0
    bank_trips: int = 0
    errors: int = 0
    hotspots_built: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def elapsed_formatted(self) -> str:
        s = int(self.elapsed_seconds)
        h, r = divmod(s, 3600)
        m, sec = divmod(r, 60)
        if h > 0:
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"

    @property
    def contracts_per_hour(self) -> float:
        elapsed_h = self.elapsed_seconds / 3600
        if elapsed_h < 0.01:
            return 0.0
        return self.contracts_completed / elapsed_h

    @property
    def xp_per_hour(self) -> float:
        elapsed_h = self.elapsed_seconds / 3600
        if elapsed_h < 0.01:
            return 0.0
        return self.total_xp / elapsed_h

    def record_contract(self, xp: int, points: int) -> None:
        self.contracts_completed += 1
        self.total_xp += xp
        self.total_points += points

    def record_hotspot(self) -> None:
        self.hotspots_built += 1

    def record_bank_trip(self) -> None:
        self.bank_trips += 1

    def record_error(self) -> None:
        self.errors += 1

    def summary(self) -> str:
        return (
            f"Session: {self.elapsed_formatted} | "
            f"Contracts: {self.contracts_completed} ({self.contracts_per_hour:.1f}/hr) | "
            f"XP: {self.total_xp:,} ({self.xp_per_hour:,.0f}/hr) | "
            f"Points: {self.total_points} | "
            f"Errors: {self.errors}"
        )
