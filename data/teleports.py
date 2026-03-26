"""
Teleport methods for reaching each of the 4 contract cities.

Supports 3 teleport types:
- Tab: Single-use teleport tablets (left-click in inventory)
- Equipment: Jewelry/cloak teleports (right-click in equipment tab)
- Spell: Standard spellbook teleports (click in spellbook)

Each method has a priority (lower = preferred) and rune requirements
for spell teleports.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class TeleportMethod:
    name: str
    method_type: str              # "tab", "equipment", "spell"
    city: str                     # Target city
    priority: int                 # Lower = preferred (1 = best)

    # For tabs: item color in inventory
    item_color: Optional[Tuple[int, int, int]] = None

    # For equipment: which equipment slot to right-click
    equipment_slot: Optional[str] = None  # "ring", "amulet", "cape"

    # For equipment: dialogue option text to select
    equipment_option: Optional[str] = None

    # For spells: which spellbook position (relative, calibrated)
    spell_name: Optional[str] = None

    # For spells: rune requirements (rune_name, count)
    rune_cost: Tuple = field(default_factory=tuple)

    # For spells: magic level required
    magic_level: int = 0


# -----------------------------------------------------------------------
# Varrock Teleports
# -----------------------------------------------------------------------

VARROCK_TAB = TeleportMethod(
    name="Varrock Teleport Tab", method_type="tab", city="varrock", priority=2,
    item_color=(160, 145, 175),
)

VARROCK_SPELL = TeleportMethod(
    name="Varrock Teleport", method_type="spell", city="varrock", priority=3,
    spell_name="Varrock Teleport", magic_level=25,
    rune_cost=(("law", 1), ("air", 3), ("fire", 1)),
)

# -----------------------------------------------------------------------
# Falador Teleports
# -----------------------------------------------------------------------

FALADOR_ROW = TeleportMethod(
    name="Ring of Wealth (Falador)", method_type="equipment", city="falador", priority=1,
    equipment_slot="ring", equipment_option="Grand Exchange",
)

FALADOR_TAB = TeleportMethod(
    name="Falador Teleport Tab", method_type="tab", city="falador", priority=2,
    item_color=(160, 145, 175),
)

FALADOR_SPELL = TeleportMethod(
    name="Falador Teleport", method_type="spell", city="falador", priority=3,
    spell_name="Falador Teleport", magic_level=37,
    rune_cost=(("law", 1), ("air", 3), ("water", 1)),
)

# -----------------------------------------------------------------------
# Ardougne Teleports
# -----------------------------------------------------------------------

ARDOUGNE_CLOAK = TeleportMethod(
    name="Ardougne Cloak", method_type="equipment", city="ardougne", priority=1,
    equipment_slot="cape", equipment_option="Monastery",
)

ARDOUGNE_TAB = TeleportMethod(
    name="Ardougne Teleport Tab", method_type="tab", city="ardougne", priority=2,
    item_color=(160, 145, 175),
)

ARDOUGNE_SPELL = TeleportMethod(
    name="Ardougne Teleport", method_type="spell", city="ardougne", priority=3,
    spell_name="Ardougne Teleport", magic_level=51,
    rune_cost=(("law", 2), ("water", 2)),
)

# -----------------------------------------------------------------------
# Hosidius Teleports
# -----------------------------------------------------------------------

HOSIDIUS_XERICS = TeleportMethod(
    name="Xeric's Talisman (Glade)", method_type="equipment", city="hosidius", priority=1,
    equipment_slot="amulet", equipment_option="Xeric's Glade",
)

HOSIDIUS_HOUSE = TeleportMethod(
    name="Teleport to House", method_type="tab", city="hosidius", priority=2,
    item_color=(160, 145, 175),
)

HOSIDIUS_HOUSE_SPELL = TeleportMethod(
    name="Teleport to House (spell)", method_type="spell", city="hosidius", priority=3,
    spell_name="Teleport to House", magic_level=40,
    rune_cost=(("law", 1), ("air", 1), ("earth", 1)),
)

# -----------------------------------------------------------------------
# Lookup by city
# -----------------------------------------------------------------------

ALL_TELEPORTS = {
    "varrock": [VARROCK_TAB, VARROCK_SPELL],
    "falador": [FALADOR_ROW, FALADOR_TAB, FALADOR_SPELL],
    "ardougne": [ARDOUGNE_CLOAK, ARDOUGNE_TAB, ARDOUGNE_SPELL],
    "hosidius": [HOSIDIUS_XERICS, HOSIDIUS_HOUSE, HOSIDIUS_HOUSE_SPELL],
}


def get_teleports_for_city(city: str) -> List[TeleportMethod]:
    """Return all teleport methods for a city, sorted by priority."""
    return sorted(ALL_TELEPORTS.get(city, []), key=lambda t: t.priority)


def resolve_teleport(city: str, settings) -> Optional[TeleportMethod]:
    """
    Pick the best available teleport for a city given current bot settings.
    Checks equipment availability and spellbook compatibility.
    """
    pref = getattr(settings, f"teleport_{city}", "auto")
    methods = get_teleports_for_city(city)

    for tp in methods:
        if pref != "auto" and tp.method_type != pref:
            continue

        # Check equipment availability
        if tp.method_type == "equipment":
            if city == "falador" and not settings.has_ring_of_wealth:
                continue
            if city == "ardougne" and not settings.has_ardougne_cloak:
                continue
            if city == "hosidius" and not settings.has_xerics_talisman:
                continue

        # Check spellbook compatibility (spell teleports need Standard spellbook)
        if tp.method_type == "spell" and settings.mode == "npc_contact":
            continue  # NPC Contact requires Lunar, can't use Standard spells

        return tp

    return None  # No valid teleport found
