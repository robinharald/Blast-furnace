"""
Master configuration for the Blast Furnace bot.

All screen positions, regions, colors, and settings are defined here.
The setup wizard populates the calibration values at runtime.
"""

import json
import os

CONFIG_FILE = "calibration.json"


class ScreenRegions:
    """
    Screen regions and positions for game UI elements.
    These are populated by the setup wizard or loaded from calibration.json.
    All coordinates are absolute screen pixels.
    """

    def __init__(self):
        # ── Game viewport ──
        self.game_x = 0
        self.game_y = 0
        self.game_w = 765
        self.game_h = 503

        # ── Inventory grid ──
        # Top-left corner of inventory slot (0,0) and slot dimensions
        self.inv_x = 563
        self.inv_y = 213
        self.inv_slot_w = 42
        self.inv_slot_h = 36
        self.inv_cols = 4
        self.inv_rows = 7

        # ── Minimap ──
        self.minimap_cx = 643
        self.minimap_cy = 83
        self.minimap_r = 72

        # ── Key clickable positions (calibrated by wizard) ──
        # Bank chest click position
        self.bank_pos = (0, 0)
        # Conveyor belt click position
        self.conveyor_pos = (0, 0)
        # Bar dispenser click position
        self.dispenser_pos = (0, 0)

        # ── Minimap walk-to points ──
        # These are minimap pixel positions to click for navigation
        self.minimap_bank = (0, 0)
        self.minimap_conveyor = (0, 0)
        self.minimap_dispenser = (0, 0)

        # ── Bank interface regions ──
        self.bank_deposit_inv_btn = (0, 0)  # "Deposit inventory" button
        self.bank_search_region = (0, 0, 0, 0)  # Search area bounds
        self.bank_close_btn = (0, 0)

        # ── Bar dispenser collection widget ──
        self.bar_collect_btn = (0, 0)  # Click to collect all bars

        # ── XP drops region (for verifying smelting) ──
        self.xp_drop_region = (0, 0, 0, 0)

    def inv_slot_center(self, slot):
        """
        Get the screen center of inventory slot (0-27).
        Slots numbered left-to-right, top-to-bottom.
        0-indexed (matching game engine and all bot frameworks).
        """
        col = slot % self.inv_cols
        row = slot // self.inv_cols
        x = self.inv_x + col * self.inv_slot_w + self.inv_slot_w // 2
        y = self.inv_y + row * self.inv_slot_h + self.inv_slot_h // 2
        return (x, y)

    def inv_slot_region(self, slot):
        """Get the bounding box (x1, y1, x2, y2) of an inventory slot (0-indexed)."""
        col = slot % self.inv_cols
        row = slot // self.inv_cols
        x1 = self.inv_x + col * self.inv_slot_w + 4
        y1 = self.inv_y + row * self.inv_slot_h + 4
        x2 = x1 + self.inv_slot_w - 8
        y2 = y1 + self.inv_slot_h - 8
        return (x1, y1, x2, y2)


class BotSettings:
    """
    Runtime settings configurable by the user.
    """

    def __init__(self):
        # Bar type (set by GUI)
        self.bar_type = None

        # Equipment toggles
        self.use_coal_bag = True
        self.use_stamina = True
        self.use_goldsmith_gauntlets = True
        self.use_ice_gloves = True

        # Coal bag locked inventory slot (0-27, 0-indexed)
        # Used for coal-requiring bars (steel/mithril/adamant/rune). Not used for gold.
        # This slot must be deposit-locked in-game so "Deposit inventory" skips it.
        self.coal_bag_slot = 0

        # Glove swap locked inventory slot (0-27, 0-indexed)
        # Used for gold bars only (goldsmith gauntlets <-> ice gloves swap).
        # Coal bars don't need a glove slot — only ice gloves are used
        # and they stay equipped (no swapping needed).
        # Never active at the same time as coal bag.
        # This slot must be deposit-locked in-game so "Deposit inventory" skips it.
        self.glove_slot = 0  # Same slot as coal bag — only one is ever active

        # Emergency stop key
        self.stop_key = "f6"

        # How long to wait for bars to smelt (ms)
        # Smelting takes ~11 ticks (~6.6s) but can vary.
        # Only matters on first trip; after that, pipelining avoids waiting.
        self.smelt_wait_ms = 8000


class Colors:
    """
    Key colors for game state detection.
    These may need calibration for different brightness/monitor settings.
    """

    # ── Bank interface ──
    BANK_BG = (61, 51, 39)              # Bank window background brown
    BANK_TITLE = (255, 152, 31)         # Orange "Bank" title text
    BANK_SLOT_EMPTY = (60, 48, 36)      # Empty bank slot

    # ── Inventory ──
    INV_EMPTY_SLOT = (62, 53, 41)       # Empty inventory slot background
    INV_SLOT_BORDER = (33, 29, 24)      # Slot border color

    # ── Minimap ──
    MINIMAP_PLAYER_DOT = (255, 255, 255)  # White player arrow/dot

    # ── Furnace objects ──
    CONVEYOR_BELT = (90, 80, 60)        # Conveyor belt color
    BAR_DISPENSER = (80, 70, 55)        # Bar dispenser color

    # ── Bar dispenser widget ──
    DISPENSER_WIDGET_BG = (65, 55, 42)  # Collection widget background
    BAR_READY_GLOW = (200, 160, 50)     # Golden glow when bars are ready

    # ── Coal ──
    COAL_DARK = (40, 35, 30)

    # ── Run energy/stamina ──
    RUN_ORB_ACTIVE = (200, 200, 50)     # Yellow when run is on
    STAMINA_ACTIVE = (230, 150, 30)     # Orange stamina effect

    # ── Chat/action indicators ──
    IDLE_INDICATOR = (0, 0, 0)          # Placeholder


# Tolerance for color matching (Euclidean distance in RGB space)
COLOR_TOLERANCE = 20
COLOR_TOLERANCE_STRICT = 10
COLOR_TOLERANCE_LOOSE = 35


def save_calibration(regions: ScreenRegions, filepath=CONFIG_FILE):
    """Save calibrated screen positions to JSON."""
    data = {}
    for attr in dir(regions):
        if not attr.startswith("_") and not callable(getattr(regions, attr)):
            data[attr] = getattr(regions, attr)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def load_calibration(regions: ScreenRegions, filepath=CONFIG_FILE):
    """Load calibrated screen positions from JSON."""
    if not os.path.exists(filepath):
        return False

    with open(filepath, "r") as f:
        data = json.load(f)

    for key, value in data.items():
        if hasattr(regions, key):
            # Convert lists back to tuples
            if isinstance(value, list):
                value = tuple(value)
            setattr(regions, key, value)

    return True
