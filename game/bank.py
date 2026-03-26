"""
Banking operations — deposit, fill plank sack, withdraw supplies.

Handles the full banking sequence:
1. Open bank
2. Deposit inventory (keeps locked items)
3. Fill plank sack (if owned)
4. Withdraw planks
5. Withdraw steel bars
6. Withdraw teleport tabs (if needed)
7. Close bank
"""
import time
import random
import logging
from typing import Optional

from config import colors
from config.settings import BotSettings, ScreenRegions
from game.object_finder import ObjectFinder
from game.inventory import InventoryReader
from game.dialogue import DialogueHandler
from screen.capture import region_has_color
from input import mouse, keyboard
from anti_detect.humanizer import Humanizer
from data.materials import get_tier

logger = logging.getLogger(__name__)


class BankHandler:
    """Full banking sequence for restocking supplies."""

    def __init__(
        self,
        settings: BotSettings,
        regions: ScreenRegions,
        finder: ObjectFinder,
        inventory: InventoryReader,
        humanizer: Humanizer,
    ):
        self.settings = settings
        self.regions = regions
        self.finder = finder
        self.inventory = inventory
        self.humanizer = humanizer
        self.tier_data = get_tier(settings.tier)

    def open_bank(self) -> bool:
        """Click the bank chest to open the bank interface."""
        bank_pos = self.finder.find_bank()
        if bank_pos is None:
            logger.warning("Bank not found in viewport")
            return False

        mouse.click(*bank_pos, variance=4)
        self.humanizer.bank_delay()

        # Wait for bank interface to appear
        return self._wait_for_bank_open(timeout=5.0)

    def _wait_for_bank_open(self, timeout: float = 5.0) -> bool:
        """Wait for bank interface to open."""
        vp = self.regions.viewport
        start = time.time()
        while time.time() - start < timeout:
            if region_has_color(
                vp.x + vp.w // 4, vp.y + vp.h // 4,
                vp.w // 2, vp.h // 2,
                colors.BANK_TITLE_BG, colors.BANK_TITLE_TOLERANCE,
                min_pixels=30,
            ):
                logger.debug("Bank interface detected")
                return True
            time.sleep(0.3)
        logger.warning("Bank open timed out")
        return False

    def deposit_all(self) -> None:
        """Click 'Deposit inventory' button (deposit-locked items stay)."""
        # The deposit button is in a fixed position relative to the bank interface
        # Approximate: near bottom-center of bank window
        vp = self.regions.viewport
        deposit_x = vp.x + vp.w // 2 - 30
        deposit_y = vp.y + vp.h - 50
        mouse.click(deposit_x, deposit_y, variance=5)
        self.humanizer.bank_delay()

    def fill_plank_sack(self) -> bool:
        """
        Fill the plank sack in bank:
        1. Withdraw 28 planks
        2. Right-click plank sack -> "Use"
        3. Planks move from inventory to sack
        """
        if not self.settings.has_plank_sack:
            return True

        logger.debug("Filling plank sack")

        # Withdraw planks to fill the sack
        self._withdraw_planks_batch(28)
        self.humanizer.bank_delay()

        # Right-click plank sack and select "Use"
        sack_slot = self.inventory.find_first_slot_with_color(
            (70, 55, 50), tolerance=30  # Plank sack color approximation
        )
        if sack_slot is not None:
            self.inventory.click_slot(sack_slot, button="right")
            self.humanizer.action_delay()
            # Select "Use" from context menu (first option usually)
            # In bank, left-click on plank sack with planks in inventory = fill
            self.inventory.click_slot(sack_slot)
            self.humanizer.bank_delay()
        else:
            logger.warning("Plank sack not found in inventory")
            return False

        return True

    def withdraw_supplies(self) -> bool:
        """Withdraw all needed supplies (planks, bars, tabs)."""
        logger.info("Withdrawing supplies")

        # Withdraw planks to fill remaining inventory slots
        self._withdraw_planks_batch(self.settings.plank_slots_available())
        self.humanizer.bank_delay()

        # Withdraw steel bars (4)
        self._withdraw_steel_bars()
        self.humanizer.bank_delay()

        # Withdraw teleport tabs if needed
        self._withdraw_teleport_tabs()
        self.humanizer.bank_delay()

        return True

    def _withdraw_planks_batch(self, count: int) -> None:
        """
        Withdraw planks from bank.
        Assumes bank tab with planks is visible and "Withdraw-All" is set.
        Click the plank slot in the bank interface.
        """
        # Bank plank position is approximate — depends on bank layout
        # The user should have planks in the first visible tab
        vp = self.regions.viewport
        plank_x = vp.x + vp.w // 4
        plank_y = vp.y + vp.h // 3
        mouse.click(plank_x, plank_y, variance=5)
        self.humanizer.bank_delay()

    def _withdraw_steel_bars(self) -> None:
        """Withdraw steel bars from bank."""
        current = self.inventory.count_steel_bars()
        if current >= 4:
            return

        vp = self.regions.viewport
        bar_x = vp.x + vp.w // 4 + 50
        bar_y = vp.y + vp.h // 3
        mouse.click(bar_x, bar_y, variance=5)

    def _withdraw_teleport_tabs(self) -> None:
        """Withdraw teleport tabs if any are missing."""
        current_tabs = self.inventory.count_teleport_tabs()
        needed = self.settings._teleport_tab_count()
        if current_tabs >= needed:
            return

        # Click tab position in bank
        vp = self.regions.viewport
        tab_x = vp.x + vp.w // 4 + 100
        tab_y = vp.y + vp.h // 3
        mouse.click(tab_x, tab_y, variance=5)

    def close_bank(self) -> None:
        """Close the bank interface."""
        keyboard.press_escape()
        self.humanizer.action_delay()

    def full_bank_sequence(self) -> bool:
        """
        Execute the complete banking sequence.
        Returns True if banking completed successfully.
        """
        logger.info("Starting full bank sequence")

        if not self.open_bank():
            return False

        self.deposit_all()

        if self.settings.has_plank_sack:
            self.fill_plank_sack()

        self.withdraw_supplies()
        self.close_bank()

        logger.info("Banking complete")
        return True
