"""
All bar types available at the Blast Furnace with their properties.
Coal requirements are halved at the Blast Furnace.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OreRequirement:
    """Defines what ores are needed for a bar."""
    primary_ore: str
    primary_color: tuple  # Approximate inventory icon color for detection
    secondary_ore: Optional[str] = None
    secondary_color: Optional[tuple] = None
    coal_per_bar: int = 0

    @property
    def requires_coal(self):
        return self.coal_per_bar > 0

    @property
    def has_two_ores(self):
        return self.secondary_ore is not None


@dataclass(frozen=True)
class BarData:
    """Complete data for a bar type."""
    name: str
    ore: OreRequirement
    bar_color: tuple        # Approximate bar color in inventory for detection
    xp_per_bar: float
    smithing_level: int

    @property
    def coal_per_bar(self):
        return self.ore.coal_per_bar

    @property
    def requires_coal(self):
        return self.ore.requires_coal


class BarType(Enum):
    """All smelting options at the Blast Furnace."""

    BRONZE = BarData(
        name="Bronze bar",
        ore=OreRequirement(
            primary_ore="Copper ore",
            primary_color=(128, 80, 48),
            secondary_ore="Tin ore",
            secondary_color=(130, 130, 130),
        ),
        bar_color=(140, 100, 50),
        xp_per_bar=6.2,
        smithing_level=1,
    )

    IRON = BarData(
        name="Iron bar",
        ore=OreRequirement(
            primary_ore="Iron ore",
            primary_color=(75, 55, 45),
        ),
        bar_color=(80, 60, 50),
        xp_per_bar=12.5,
        smithing_level=15,
    )

    SILVER = BarData(
        name="Silver bar",
        ore=OreRequirement(
            primary_ore="Silver ore",
            primary_color=(192, 192, 192),
        ),
        bar_color=(200, 200, 200),
        xp_per_bar=13.7,
        smithing_level=20,
    )

    STEEL = BarData(
        name="Steel bar",
        ore=OreRequirement(
            primary_ore="Iron ore",
            primary_color=(75, 55, 45),
            coal_per_bar=1,
        ),
        bar_color=(110, 110, 110),
        xp_per_bar=17.5,
        smithing_level=30,
    )

    GOLD = BarData(
        name="Gold bar",
        ore=OreRequirement(
            primary_ore="Gold ore",
            primary_color=(200, 170, 40),
        ),
        bar_color=(220, 190, 50),
        xp_per_bar=22.5,  # 56.2 with goldsmith gauntlets
        smithing_level=40,
    )

    MITHRIL = BarData(
        name="Mithril bar",
        ore=OreRequirement(
            primary_ore="Mithril ore",
            primary_color=(60, 60, 130),
            coal_per_bar=2,
        ),
        bar_color=(70, 70, 150),
        xp_per_bar=30.0,
        smithing_level=50,
    )

    ADAMANTITE = BarData(
        name="Adamantite bar",
        ore=OreRequirement(
            primary_ore="Adamantite ore",
            primary_color=(60, 100, 60),
            coal_per_bar=3,
        ),
        bar_color=(80, 120, 80),
        xp_per_bar=37.5,
        smithing_level=70,
    )

    RUNITE = BarData(
        name="Runite bar",
        ore=OreRequirement(
            primary_ore="Runite ore",
            primary_color=(50, 130, 130),
            coal_per_bar=4,
        ),
        bar_color=(60, 150, 150),
        xp_per_bar=50.0,
        smithing_level=85,
    )

    @property
    def data(self) -> BarData:
        return self.value

    def __str__(self):
        return self.value.name


# Coal constants
COAL_COLOR = (40, 35, 30)   # Dark brown/black coal icon
COAL_NAME = "Coal"

# Goldsmith gauntlets XP bonus for gold
GOLD_GAUNTLETS_XP = 56.2
