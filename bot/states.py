"""
Bot state enumeration — all 24 states for the Mahogany Homes bot.
"""
from enum import Enum, auto


class BotState(Enum):
    # Initialization
    STARTING = auto()

    # Banking
    BANKING = auto()
    FILLING_PLANK_SACK = auto()
    WITHDRAWING_SUPPLIES = auto()

    # Contract acquisition — Mode A (NPC Contact)
    CASTING_NPC_CONTACT = auto()
    SELECTING_NPC_CONTACT = auto()
    SELECTING_TIER = auto()

    # Contract acquisition — Mode B (Walk-to-Contractor)
    WALKING_TO_CONTRACTOR = auto()
    TALKING_TO_CONTRACTOR = auto()
    SELECTING_TIER_CONTRACTOR = auto()

    # Contract parsing (both modes)
    PARSING_CONTRACT = auto()

    # Travel
    TELEPORTING = auto()
    WAITING_FOR_TELEPORT = auto()
    WALKING_TO_HOUSE = auto()
    ENTERING_HOUSE = auto()

    # Work
    SCANNING_HOTSPOTS = auto()
    ROTATING_CAMERA = auto()
    INTERACTING_HOTSPOT = auto()
    WAITING_FOR_BUILD = auto()
    CHANGING_FLOOR = auto()

    # Completion
    TALKING_TO_HOMEOWNER = auto()
    HANDLING_COMPLETION_DIALOGUE = auto()

    # Error handling
    RECOVERING = auto()

    # Terminal
    STOPPED = auto()
