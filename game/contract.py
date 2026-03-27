"""
Contract parsing, assignment tracking, and NPC lookup.

Parses contract assignments from chat text via OCR and maintains
the current contract state (which NPC, which city, which tier).
"""
import logging
from typing import Optional
from dataclasses import dataclass

from data.npcs import HouseNPC, get_npc, NPC_NAMES
from data.materials import TierData, get_tier
from screen.ocr import (
    read_chat_text, find_npc_name_in_text, parse_tier_from_text,
    is_contract_finished, is_no_materials,
)
from config.settings import ScreenRegions

logger = logging.getLogger(__name__)


@dataclass
class ContractState:
    """Current contract tracking."""
    npc: Optional[HouseNPC] = None
    tier: Optional[TierData] = None
    is_active: bool = False
    hotspots_completed: int = 0
    visited_upstairs: bool = False

    def reset(self) -> None:
        self.npc = None
        self.tier = None
        self.is_active = False
        self.hotspots_completed = 0
        self.visited_upstairs = False


class ContractManager:
    """Parse and track Mahogany Homes contracts."""

    def __init__(self, regions: ScreenRegions, default_tier: str = "expert"):
        self.regions = regions
        self.default_tier = default_tier
        self.state = ContractState()

    def parse_contract_from_chat(self) -> Optional[str]:
        """
        OCR the chat box and extract the assigned NPC name.
        Returns NPC key (lowercase) or None.
        """
        text = read_chat_text(
            self.regions.chat_box.x, self.regions.chat_box.y,
            self.regions.chat_box.w, self.regions.chat_box.h,
        )
        if not text:
            logger.warning("OCR returned empty text from chat box")
            return None

        logger.debug(f"Chat OCR: {text[:100]}...")

        # Check for completion first
        if is_contract_finished(text):
            logger.info("Contract finished detected in chat")
            self.state.is_active = False
            return None

        # Check for no materials
        if is_no_materials(text):
            logger.warning("No materials detected — need to bank")
            return None

        # Try to find NPC name
        npc_name = find_npc_name_in_text(text)
        if npc_name:
            logger.info(f"Contract parsed: NPC = {npc_name}")
            self.state.npc = get_npc(npc_name)
            self.state.is_active = True
            self.state.hotspots_completed = 0
            self.state.visited_upstairs = False

            # Try to parse tier
            tier_key = parse_tier_from_text(text)
            if tier_key:
                self.state.tier = get_tier(tier_key)
            else:
                self.state.tier = get_tier(self.default_tier)

            return npc_name

        return None

    def set_contract(self, npc_name: str, tier_key: Optional[str] = None) -> None:
        """Manually set the current contract (for testing or recovery)."""
        self.state.npc = get_npc(npc_name)
        self.state.tier = get_tier(tier_key or self.default_tier)
        self.state.is_active = True
        self.state.hotspots_completed = 0
        self.state.visited_upstairs = False

    def mark_hotspot_done(self) -> None:
        """Increment hotspot completion counter."""
        self.state.hotspots_completed += 1

    def mark_complete(self) -> None:
        """Mark the current contract as complete."""
        self.state.is_active = False
        logger.info(f"Contract completed: {self.state.npc.name if self.state.npc else 'unknown'}")

    @property
    def current_npc(self) -> Optional[HouseNPC]:
        return self.state.npc

    @property
    def current_city(self) -> Optional[str]:
        return self.state.npc.city if self.state.npc else None

    @property
    def has_active_contract(self) -> bool:
        return self.state.is_active and self.state.npc is not None

    @property
    def needs_upstairs(self) -> bool:
        return (
            self.state.npc is not None
            and self.state.npc.has_upstairs
            and not self.state.visited_upstairs
        )
