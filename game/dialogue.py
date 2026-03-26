"""
NPC dialogue detection and navigation.

Detects dialogue boxes by checking for the brown background color
at the known chat box region. Handles:
- "Click here to continue" (SPACE)
- Multi-option selection (number keys 1-5)
- Contract assignment dialogue
- Completion dialogue with tea option
"""
import logging
import time
import random
from typing import Optional

from config import colors
from config.settings import ScreenRegions
from screen.capture import region_has_color, find_color_in_region
from input import keyboard

logger = logging.getLogger(__name__)


class DialogueHandler:
    """Detect and navigate NPC dialogue boxes."""

    def __init__(self, regions: ScreenRegions):
        self.regions = regions
        self._chat = regions.chat_box

    def is_dialogue_open(self) -> bool:
        """Check if any dialogue box is visible."""
        return region_has_color(
            self._chat.x, self._chat.y, self._chat.w, self._chat.h,
            colors.DIALOGUE_BG, colors.DIALOGUE_BG_TOLERANCE,
            min_pixels=50,
        )

    def click_continue(self) -> None:
        """Press SPACE to advance 'Click here to continue' dialogue."""
        keyboard.press_space()
        time.sleep(random.uniform(0.3, 0.6))

    def select_option(self, option_number: int) -> None:
        """Select a numbered dialogue option (1-5) by pressing the number key."""
        keyboard.press_number(option_number)
        time.sleep(random.uniform(0.3, 0.6))

    def dismiss_all(self) -> None:
        """Try to dismiss any open dialogue by pressing ESC then SPACE."""
        keyboard.press_escape()
        time.sleep(random.uniform(0.2, 0.4))
        if self.is_dialogue_open():
            keyboard.press_space()
            time.sleep(random.uniform(0.2, 0.4))

    def handle_contract_dialogue(self, tier_option: int = 4) -> bool:
        """
        Navigate the full contractor dialogue sequence.

        1. SPACE through initial text
        2. Select "I'd like a construction contract" (option 1)
        3. Select tier (option number based on tier)
        4. SPACE through assignment text

        Returns True if dialogue completed successfully.
        """
        for _ in range(15):
            if not self.is_dialogue_open():
                return True

            # Try selecting the construction contract option first
            self.click_continue()
            time.sleep(random.uniform(0.4, 0.8))

        return False

    def handle_tier_selection(self, tier: str) -> None:
        """Select the contract tier in the dialogue options."""
        tier_map = {
            "beginner": 1,
            "novice": 2,
            "adept": 3,
            "expert": 4,
        }
        option = tier_map.get(tier, 4)

        if self.is_dialogue_open():
            self.select_option(option)
            time.sleep(random.uniform(0.4, 0.7))

    def handle_completion_dialogue(self, accept_tea: bool = False) -> bool:
        """
        Navigate the homeowner completion dialogue.

        1. Player: "I've finished with the work you wanted." (SPACE)
        2. Homeowner: "Would you like a cup of tea?" (SPACE)
        3. Select: "Yes, I'd love a cuppa" (1) or "No thanks" (2)

        Returns True if dialogue completed.
        """
        for _ in range(10):
            if not self.is_dialogue_open():
                return True

            self.click_continue()
            time.sleep(random.uniform(0.4, 0.8))

            # Check if we're at the tea option
            if self.is_dialogue_open():
                if accept_tea:
                    self.select_option(1)  # "Yes, I'd love a cuppa"
                else:
                    self.select_option(2)  # "No thanks, I better be off"
                time.sleep(random.uniform(0.3, 0.6))

        # Final dismiss
        for _ in range(5):
            if not self.is_dialogue_open():
                return True
            self.click_continue()
            time.sleep(random.uniform(0.3, 0.5))

        return not self.is_dialogue_open()

    def wait_for_dialogue(self, timeout: float = 5.0) -> bool:
        """Wait for a dialogue to appear, with timeout."""
        start = time.time()
        while time.time() - start < timeout:
            if self.is_dialogue_open():
                return True
            time.sleep(0.2)
        return False
