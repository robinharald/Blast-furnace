"""
All color constants used by the bot.

Colors are RGB tuples. Tolerance values define the maximum Euclidean
distance in RGB space for a pixel to be considered a match.

RuneLite overlay colors must match what the user configures in their plugins.
Item colors are approximate centers of the item sprite color distribution.
"""

# ---------------------------------------------------------------------------
# RuneLite Plugin Overlay Colors (user-configurable, these are defaults)
# ---------------------------------------------------------------------------
HOTSPOT_HIGHLIGHT = (0, 255, 255)       # Cyan — Mahogany Homes plugin hotspot overlay
HOTSPOT_TOLERANCE = 30

DOOR_MARKER = (255, 165, 0)             # Orange — Object Markers: house doors
DOOR_TOLERANCE = 35

STAIRCASE_MARKER = (255, 255, 0)        # Yellow — Object Markers: staircases
STAIRCASE_TOLERANCE = 30

BANK_MARKER = (0, 0, 255)              # Blue — Object Markers: bank chest
BANK_TOLERANCE = 30

NPC_MARKER = (255, 0, 255)             # Magenta — NPC Indicators: homeowner NPCs
NPC_TOLERANCE = 30

CONTRACTOR_MARKER = (0, 255, 0)        # Lime — NPC Indicators: contractor NPCs (Mode B)
CONTRACTOR_TOLERANCE = 30

# ---------------------------------------------------------------------------
# Inventory Item Colors (approximate, with generous tolerance)
# ---------------------------------------------------------------------------
# Planks (center color of sprite)
PLANK_REGULAR = (170, 135, 75)
PLANK_OAK = (155, 120, 55)
PLANK_TEAK = (130, 95, 45)
PLANK_MAHOGANY = (100, 55, 30)
PLANK_TOLERANCE = 25

STEEL_BAR = (115, 115, 120)
STEEL_BAR_TOLERANCE = 25

# Teleport tabs (distinct blue/purple tint)
TELEPORT_TAB = (160, 145, 175)
TELEPORT_TAB_TOLERANCE = 30

# Rune pouch
RUNE_POUCH = (70, 55, 85)
RUNE_POUCH_TOLERANCE = 25

# Empty inventory slot background
INV_EMPTY_SLOT = (62, 53, 41)
INV_EMPTY_TOLERANCE = 20

# ---------------------------------------------------------------------------
# UI Detection Colors
# ---------------------------------------------------------------------------
# Dialogue box (brown background)
DIALOGUE_BG = (101, 75, 51)
DIALOGUE_BG_TOLERANCE = 25

# Bank interface title bar
BANK_TITLE_BG = (57, 49, 35)
BANK_TITLE_TOLERANCE = 20

# Chat text colors
CHAT_TEXT_WHITE = (255, 255, 255)
CHAT_TEXT_YELLOW = (255, 255, 0)
CHAT_TEXT_TOLERANCE = 30

# Run orb (green when full, yellow mid, red low)
RUN_ORB_HIGH = (120, 180, 80)       # > 50% energy
RUN_ORB_LOW = (200, 100, 50)        # < 20% energy
RUN_ORB_TOLERANCE = 40

# Spellbook — NPC Contact icon tint (when castable vs grayed)
NPC_CONTACT_ACTIVE = (75, 130, 185)
NPC_CONTACT_GRAYED = (50, 50, 55)
SPELL_TOLERANCE = 30

# Login / disconnect screen
LOGIN_SCREEN_BG = (0, 0, 0)
LOGIN_TOLERANCE = 10


def plank_color_for_tier(tier: str) -> tuple:
    """Return the plank color for a given contract tier."""
    return {
        "beginner": PLANK_REGULAR,
        "novice": PLANK_OAK,
        "adept": PLANK_TEAK,
        "expert": PLANK_MAHOGANY,
    }[tier]
