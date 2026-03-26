"""
NPC Contact spell casting and interface navigation.

Used in Mode A to get new contracts without walking to a contractor.
Requires Lunar spellbook active and 67 Magic.
"""
import time
import random
import logging
from typing import Optional

from config import colors
from config.settings import ScreenRegions
from screen.capture import region_has_color, find_color_in_region
from input import mouse, keyboard
from anti_detect.humanizer import Humanizer

logger = logging.getLogger(__name__)


class SpellCaster:
    """Cast NPC Contact and navigate the contact interface."""

    def __init__(self, regions: ScreenRegions, humanizer: Humanizer):
        self.regions = regions
        self.humanizer = humanizer
        self._first_contact_done = False

    def cast_npc_contact(self) -> bool:
        """
        Cast the NPC Contact spell.

        If first time: Open spellbook -> click NPC Contact -> select contractor.
        Subsequent: Right-click NPC Contact -> "Last contacted" (faster).

        Returns True if the spell was cast (dialogue should appear).
        """
        if self._first_contact_done:
            return self._recontact_last()

        return self._cast_fresh()

    def _cast_fresh(self) -> bool:
        """First-time cast: open spellbook, find and click NPC Contact."""
        logger.info("Casting NPC Contact (first time)")

        # Open spellbook tab
        keyboard.press_f_key(6)
        self.humanizer.action_delay()

        # Find NPC Contact spell by its blue color
        vp = self.regions.viewport
        spell_pos = find_color_in_region(
            vp.x, vp.y, vp.w, vp.h,
            colors.NPC_CONTACT_ACTIVE, colors.SPELL_TOLERANCE,
            min_pixels=5,
        )

        if spell_pos is None:
            logger.warning("NPC Contact spell not found (grayed out or wrong spellbook?)")
            # Switch back to inventory
            keyboard.press_f_key(3)
            return False

        mouse.click(*spell_pos, variance=3)
        self.humanizer.reaction_delay()

        # Wait for NPC selection interface
        time.sleep(random.uniform(1.0, 2.0))

        # Select the contractor (Amy is the primary contact)
        # The interface shows a list of NPCs — we need to find and click "Amy"
        # For now, use the first option or search for Amy's icon
        self._select_contractor_in_list()

        # Switch back to inventory tab
        keyboard.press_f_key(3)

        self._first_contact_done = True
        return True

    def _recontact_last(self) -> bool:
        """
        Subsequent casts: right-click NPC Contact -> "Last contacted".
        This skips the NPC selection interface.
        """
        logger.info("Casting NPC Contact (re-contact last)")

        # Open spellbook tab
        keyboard.press_f_key(6)
        self.humanizer.action_delay()

        # Find NPC Contact spell
        vp = self.regions.viewport
        spell_pos = find_color_in_region(
            vp.x, vp.y, vp.w, vp.h,
            colors.NPC_CONTACT_ACTIVE, colors.SPELL_TOLERANCE,
            min_pixels=5,
        )

        if spell_pos is None:
            logger.warning("NPC Contact spell not found")
            keyboard.press_f_key(3)
            return False

        # Right-click for "Last contacted" option
        mouse.right_click(*spell_pos, variance=3)
        self.humanizer.action_delay()

        # Select "Last contacted" — usually the 2nd option in context menu
        # Click slightly below the right-click position
        mouse.click(spell_pos[0], spell_pos[1] + 20, variance=2)
        self.humanizer.reaction_delay()

        # Switch back to inventory tab
        keyboard.press_f_key(3)
        return True

    def _select_contractor_in_list(self) -> bool:
        """
        In the NPC Contact interface, select the contractor.
        The interface shows a scrollable list of NPCs.
        Amy is the primary contractor to select.
        """
        logger.debug("Selecting contractor in NPC Contact list")

        # The NPC Contact interface is a chat-style selector
        # Amy should be near the top of available contacts
        # Press SPACE or click through to find her
        # This is simplified — real implementation may need to scroll/search

        time.sleep(random.uniform(0.5, 1.0))

        # Try clicking continue through the interface
        for _ in range(5):
            keyboard.press_space()
            time.sleep(random.uniform(0.4, 0.7))

        return True

    def is_spell_available(self) -> bool:
        """Check if NPC Contact spell is castable (not grayed out)."""
        vp = self.regions.viewport
        result = find_color_in_region(
            vp.x, vp.y, vp.w, vp.h,
            colors.NPC_CONTACT_ACTIVE, colors.SPELL_TOLERANCE,
            min_pixels=3,
        )
        return result is not None
