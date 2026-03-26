"""
Contract tier data — plank types, material requirements, XP, and points.
"""
from dataclasses import dataclass
from typing import Tuple

from config.colors import (
    PLANK_REGULAR, PLANK_OAK, PLANK_TEAK, PLANK_MAHOGANY, PLANK_TOLERANCE,
)


@dataclass(frozen=True)
class TierData:
    name: str                          # Display name
    key: str                           # Config key
    construction_level: int            # Minimum level
    plank_type: str                    # Item name
    plank_color: Tuple[int, int, int]  # Inventory sprite color
    plank_tolerance: int               # Color match tolerance
    min_planks_per_contract: int       # Best-case planks needed
    max_planks_per_contract: int       # Worst-case planks needed
    steel_bar_chance: float            # Probability a contract needs steel bars
    max_steel_bars: int                # Max bars per contract
    avg_xp_per_contract: int           # Average construction XP
    points_per_contract: int           # Carpenter points rewarded


BEGINNER = TierData(
    name="Beginner", key="beginner", construction_level=1,
    plank_type="Plank", plank_color=PLANK_REGULAR, plank_tolerance=PLANK_TOLERANCE,
    min_planks_per_contract=8, max_planks_per_contract=11,
    steel_bar_chance=0.33, max_steel_bars=1,
    avg_xp_per_contract=950, points_per_contract=2,
)

NOVICE = TierData(
    name="Novice", key="novice", construction_level=20,
    plank_type="Oak plank", plank_color=PLANK_OAK, plank_tolerance=PLANK_TOLERANCE,
    min_planks_per_contract=8, max_planks_per_contract=11,
    steel_bar_chance=0.33, max_steel_bars=1,
    avg_xp_per_contract=1900, points_per_contract=3,
)

ADEPT = TierData(
    name="Adept", key="adept", construction_level=50,
    plank_type="Teak plank", plank_color=PLANK_TEAK, plank_tolerance=PLANK_TOLERANCE,
    min_planks_per_contract=8, max_planks_per_contract=11,
    steel_bar_chance=1.0, max_steel_bars=1,
    avg_xp_per_contract=3260, points_per_contract=4,
)

EXPERT = TierData(
    name="Expert", key="expert", construction_level=70,
    plank_type="Mahogany plank", plank_color=PLANK_MAHOGANY, plank_tolerance=PLANK_TOLERANCE,
    min_planks_per_contract=10, max_planks_per_contract=11,
    steel_bar_chance=0.67, max_steel_bars=1,
    avg_xp_per_contract=4380, points_per_contract=5,
)

ALL_TIERS = {
    "beginner": BEGINNER,
    "novice": NOVICE,
    "adept": ADEPT,
    "expert": EXPERT,
}


def get_tier(key: str) -> TierData:
    """Look up tier data by key."""
    return ALL_TIERS[key.lower()]
