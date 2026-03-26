"""
Screen regions, bot settings, and calibration persistence.
All screen coordinates are absolute (monitor-level).
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple

CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "calibration.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")

# OSRS inventory layout constants (standard client)
INV_COLS = 4
INV_ROWS = 7
INV_SLOT_SPACING_X = 42
INV_SLOT_SPACING_Y = 36


@dataclass
class Region:
    """A rectangular screen region defined by top-left (x, y) and dimensions."""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    @property
    def center(self) -> Tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h


@dataclass
class Point:
    """A single screen coordinate."""
    x: int = 0
    y: int = 0


@dataclass
class ScreenRegions:
    """All calibrated screen regions — derived from wizard clicks."""
    viewport: Region = field(default_factory=Region)
    inventory_origin: Point = field(default_factory=Point)  # top-left of slot 0
    chat_box: Region = field(default_factory=Region)
    minimap_center: Point = field(default_factory=Point)
    run_orb: Point = field(default_factory=Point)
    spellbook_tab: Point = field(default_factory=Point)
    equipment_tab: Point = field(default_factory=Point)

    def inventory_slot_center(self, slot: int) -> Tuple[int, int]:
        """Return absolute (x, y) center of the given inventory slot (0-27)."""
        col = slot % INV_COLS
        row = slot // INV_COLS
        x = self.inventory_origin.x + col * INV_SLOT_SPACING_X
        y = self.inventory_origin.y + row * INV_SLOT_SPACING_Y
        return x, y

    def all_inventory_slots(self) -> list:
        """Return list of (x, y) centers for all 28 slots."""
        return [self.inventory_slot_center(i) for i in range(INV_COLS * INV_ROWS)]


@dataclass
class BotSettings:
    """User-configurable settings from the GUI."""
    # Contract
    tier: str = "expert"  # beginner / novice / adept / expert
    mode: str = "npc_contact"  # npc_contact / walk_to_contractor
    construction_level: int = 70

    # Teleport per city: "tab", "spell", "equipment", "auto"
    teleport_varrock: str = "auto"
    teleport_falador: str = "auto"
    teleport_ardougne: str = "auto"
    teleport_hosidius: str = "auto"

    # Equipment flags
    has_imcando_hammer: bool = False
    has_amys_saw: bool = False
    has_plank_sack: bool = False
    has_xerics_talisman: bool = False
    has_ring_of_wealth: bool = False
    has_ardougne_cloak: bool = False

    # Anti-detection
    anti_detection_level: str = "medium"  # low / medium / high
    session_length_minutes: int = 90

    # Controls
    stop_key: str = "F8"

    def locked_slot_count(self) -> int:
        """How many inventory slots are occupied by non-plank items."""
        count = 0
        if not self.has_imcando_hammer:
            count += 1  # hammer
        if not self.has_amys_saw:
            count += 1  # saw
        if self.has_plank_sack:
            count += 1
        if self.mode == "npc_contact":
            count += 1  # rune pouch for NPC Contact
        # Steel bars (always 4)
        count += 4
        # Teleport tabs (count those not covered by equipment)
        count += self._teleport_tab_count()
        return count

    def _teleport_tab_count(self) -> int:
        """Count how many teleport tab inventory slots are needed."""
        count = 0
        tp_map = {
            "varrock": self.teleport_varrock,
            "falador": self.teleport_falador,
            "ardougne": self.teleport_ardougne,
            "hosidius": self.teleport_hosidius,
        }
        for city, method in tp_map.items():
            if method == "auto":
                # Auto resolves at runtime: equipment > tab > spell
                if city == "falador" and self.has_ring_of_wealth:
                    continue
                if city == "ardougne" and self.has_ardougne_cloak:
                    continue
                if city == "hosidius" and self.has_xerics_talisman:
                    continue
                count += 1  # needs a tab
            elif method == "tab":
                count += 1
            # "equipment" and "spell" don't use inventory slots
        return count

    def plank_slots_available(self) -> int:
        """Number of inventory slots available for planks."""
        return 28 - self.locked_slot_count()


def save_calibration(regions: ScreenRegions) -> None:
    """Persist calibration data to disk."""
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(asdict(regions), f, indent=2)


def load_calibration() -> Optional[ScreenRegions]:
    """Load calibration from disk, or None if not found."""
    if not os.path.exists(CALIBRATION_FILE):
        return None
    try:
        with open(CALIBRATION_FILE) as f:
            data = json.load(f)
        regions = ScreenRegions()
        regions.viewport = Region(**data.get("viewport", {}))
        regions.inventory_origin = Point(**data.get("inventory_origin", {}))
        regions.chat_box = Region(**data.get("chat_box", {}))
        regions.minimap_center = Point(**data.get("minimap_center", {}))
        regions.run_orb = Point(**data.get("run_orb", {}))
        regions.spellbook_tab = Point(**data.get("spellbook_tab", {}))
        regions.equipment_tab = Point(**data.get("equipment_tab", {}))
        return regions
    except (json.JSONDecodeError, TypeError):
        return None


def save_settings(settings: BotSettings) -> None:
    """Persist bot settings to disk."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(asdict(settings), f, indent=2)


def load_settings() -> BotSettings:
    """Load bot settings from disk, or return defaults."""
    if not os.path.exists(SETTINGS_FILE):
        return BotSettings()
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        return BotSettings(**{k: v for k, v in data.items() if k in BotSettings.__dataclass_fields__})
    except (json.JSONDecodeError, TypeError):
        return BotSettings()
