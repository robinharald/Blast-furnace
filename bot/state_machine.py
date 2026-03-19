"""
Main bot state machine.

Every state transition validates prerequisites before acting.
Every click verifies its result before moving on.
Robust error recovery with retry logic.
"""

import time
import keyboard

from bot.states import BotState
from bot.session import SessionStats
from config import ScreenRegions, BotSettings
from game.inventory import InventoryReader
from game.coal_bag import CoalBagManager
from game.bank import BankHandler
from game.furnace import FurnaceHandler
from anti_detect.humanizer import Humanizer
from data.bars import BarType


class BlastFurnaceStateMachine:
    """
    The core loop. Each state is a method that:
    1. Validates preconditions
    2. Performs the action with retries
    3. Verifies the result
    4. Transitions to the next state

    If any step fails after retries, it falls back to a safe state (BANKING).
    """

    MAX_RETRIES = 3
    MAX_CONSECUTIVE_ERRORS = 10

    def __init__(self, regions: ScreenRegions, settings: BotSettings):
        self.regions = regions
        self.settings = settings
        self.humanizer = Humanizer()

        # Build handler chain
        self.inventory = InventoryReader(regions, self.humanizer)
        self.coal_bag = CoalBagManager(
            settings.coal_bag_slot, regions, self.inventory, self.humanizer
        ) if settings.use_coal_bag else None
        self.bank = BankHandler(
            regions, settings, self.inventory, self.coal_bag, self.humanizer
        )
        self.furnace = FurnaceHandler(
            regions, settings, self.inventory, self.coal_bag, self.humanizer
        )

        self.stats = SessionStats(
            settings.bar_type,
            use_goldsmith=(settings.use_goldsmith_gauntlets and settings.bar_type == BarType.GOLD)
        )

        self.state = BotState.STARTING
        self._consecutive_errors = 0
        self._running = True

        # Track whether this trip deposits ore (triggers smelting)
        self._is_ore_trip = True
        self._items_deposited_this_trip = 0

    def run(self):
        """Main loop. Runs until stopped or fatal error."""
        print(f"\n  Starting Blast Furnace Bot")
        print(f"  Bar type: {self.settings.bar_type.data.name}")
        print(f"  Coal bag: {'Yes (slot ' + str(self.settings.coal_bag_slot) + ')' if self.settings.use_coal_bag else 'No'}")
        print(f"  Stamina:  {'Yes' if self.settings.use_stamina else 'No'}")
        print(f"  Stop key: {self.settings.stop_key.upper()}")
        print(f"  Press {self.settings.stop_key.upper()} at any time to stop.\n")

        # Register stop key
        keyboard.on_press_key(self.settings.stop_key, lambda _: self.stop())

        self.state = BotState.BANKING

        while self._running and self.state != BotState.STOPPED:
            try:
                self._tick()

                # Check for consecutive errors
                if self._consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    print(f"\n  [ERROR] Too many consecutive errors ({self._consecutive_errors}). Stopping.")
                    self.state = BotState.STOPPED
                    break

                # Anti-detection: micro-breaks, mouse drift
                self.humanizer.maybe_micro_break()
                self.humanizer.maybe_mouse_drift()

                # Periodic long breaks
                if self.humanizer.should_take_break():
                    print("  [BREAK] Taking a short break...")
                    self.stats.breaks_taken += 1
                    self.humanizer.take_long_break()
                    print("  [BREAK] Back to work.")

            except KeyboardInterrupt:
                print("\n  Interrupted by user.")
                self.state = BotState.STOPPED
            except Exception as e:
                print(f"  [ERROR] Unexpected: {e}")
                self._consecutive_errors += 1
                self.stats.add_error()
                self.humanizer.transition_delay()
                # Try to recover by going to bank
                self.state = BotState.WALKING_TO_BANK

        # Cleanup
        keyboard.unhook_all()
        print(self.stats.summary())

    def stop(self):
        """Signal the bot to stop."""
        print("\n  [STOP] Stop key pressed. Finishing current action...")
        self._running = False

    def _tick(self):
        """Execute one state machine tick."""
        handlers = {
            BotState.BANKING: self._handle_banking,
            BotState.WALKING_TO_CONVEYOR: self._handle_walk_to_conveyor,
            BotState.DEPOSITING_ORE: self._handle_deposit_ore,
            BotState.WALKING_TO_DISPENSER: self._handle_walk_to_dispenser,
            BotState.WAITING_FOR_BARS: self._handle_waiting_for_bars,
            BotState.COLLECTING_BARS: self._handle_collect_bars,
            BotState.WALKING_TO_BANK: self._handle_walk_to_bank,
        }

        handler = handlers.get(self.state)
        if handler:
            handler()
        else:
            self.state = BotState.BANKING

    # ── State handlers ──

    def _handle_banking(self):
        """
        BANKING state:
        1. Open bank
        2. Check supplies
        3. Deposit bars/items (except coal bag)
        4. Handle stamina if enabled
        5. Withdraw ores for next trip
        6. Close bank
        7. Transition to WALKING_TO_CONVEYOR
        """
        print(f"  [{self.stats.elapsed_formatted}] Banking... {self.stats.status_line()}")

        # Step 1: Open bank with retry
        for attempt in range(self.MAX_RETRIES):
            if self.bank.open_bank():
                break
            print(f"    Retry opening bank ({attempt + 1}/{self.MAX_RETRIES})")
            self.humanizer.transition_delay()
        else:
            self._error("Failed to open bank")
            self.state = BotState.WALKING_TO_BANK
            return

        # Step 2: Check if we have supplies
        if not self.bank.has_supplies(self.settings.bar_type):
            print("  [DONE] Out of supplies!")
            self.state = BotState.STOPPED
            return

        # Step 3: Deposit inventory (except coal bag)
        self.bank.deposit_all_except_coal_bag()
        self.humanizer.bank_delay()

        # Step 4: Stamina management
        if self.settings.use_stamina:
            self.bank.handle_stamina()

        # Step 5: Withdraw ores
        if not self.bank.withdraw_ore(self.settings.bar_type):
            self._error("Failed to withdraw ores")
            return

        # Track if this is an ore trip (for coal-requiring bars)
        self._is_ore_trip = self.bank.is_ore_trip(self.settings.bar_type)
        coal_bag_slot = self.coal_bag.get_locked_slot() if self.settings.use_coal_bag else None
        self._items_deposited_this_trip = self.inventory.count_filled_slots(
            exclude_slot=coal_bag_slot
        )

        # Step 6: Close bank
        self.bank.close_bank()
        self.humanizer.transition_delay()

        # Step 7: For gold bars, ensure goldsmith gauntlets are equipped
        if self.settings.bar_type == BarType.GOLD and self.settings.use_goldsmith_gauntlets:
            self.furnace.swap_to_goldsmith_gauntlets()

        # Step 8: Transition
        self.stats.add_trip()
        self._consecutive_errors = 0
        self.state = BotState.WALKING_TO_CONVEYOR

    def _handle_walk_to_conveyor(self):
        """Walk from bank to conveyor belt."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to conveyor...")
        self.furnace.walk_to_conveyor()
        self.humanizer.action_delay()
        self.state = BotState.DEPOSITING_ORE

    def _handle_deposit_ore(self):
        """
        Deposit ores on the conveyor belt.
        Handles coal bag emptying and multi-step deposits.
        """
        print(f"  [{self.stats.elapsed_formatted}] Depositing ore on conveyor...")

        for attempt in range(self.MAX_RETRIES):
            if self.furnace.deposit_on_conveyor(self.settings.bar_type):
                break
            print(f"    Retry deposit ({attempt + 1}/{self.MAX_RETRIES})")
            self.humanizer.transition_delay()
        else:
            self._error("Failed to deposit ore on conveyor")
            self.state = BotState.WALKING_TO_BANK
            return

        # Track ore/coal usage
        bar = self.settings.bar_type
        if self._is_ore_trip:
            self.stats.add_ore(self._items_deposited_this_trip)
        else:
            self.stats.add_coal(self._items_deposited_this_trip)
            if self.settings.use_coal_bag:
                self.stats.add_coal(27)  # Coal from bag

        self._consecutive_errors = 0

        # Decide next state
        if self._is_ore_trip:
            # Ore was deposited — bars will smelt. Go collect.
            self.state = BotState.WALKING_TO_DISPENSER
        else:
            # Coal-only trip — go back for more coal or ore
            self.state = BotState.WALKING_TO_BANK

    def _handle_walk_to_dispenser(self):
        """Walk from conveyor to bar dispenser."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to dispenser...")
        self.furnace.walk_to_dispenser()
        self.humanizer.action_delay()
        self.state = BotState.WAITING_FOR_BARS

    def _handle_waiting_for_bars(self):
        """
        Wait for bars to finish smelting.
        The bars smelt nearly instantly at the Blast Furnace,
        but we add a brief wait and verify.
        """
        print(f"  [{self.stats.elapsed_formatted}] Waiting for bars to smelt...")

        # Bars at BF smelt very quickly (within 1-2 ticks)
        # Wait a moment then try to collect
        self.humanizer.tick_delay()
        self.humanizer.tick_delay()

        # Check if bars are ready (with timeout)
        if self.furnace.wait_for_bars(timeout=self.settings.smelt_wait_ms / 1000.0):
            self.state = BotState.COLLECTING_BARS
        else:
            # Bars might still be ready even if detection missed it.
            # Try collecting anyway.
            self.state = BotState.COLLECTING_BARS

    def _handle_collect_bars(self):
        """
        Collect bars from the bar dispenser.
        Swaps gloves if needed (ice gloves for gold bars).
        """
        print(f"  [{self.stats.elapsed_formatted}] Collecting bars...")

        # Swap to ice gloves before collecting (hot bars)
        if self.settings.bar_type == BarType.GOLD and self.settings.use_ice_gloves:
            self.furnace.swap_to_ice_gloves()

        # Collect bars
        bars_collected = 0
        for attempt in range(self.MAX_RETRIES):
            bars_collected = self.furnace.collect_bars(self.settings.bar_type)
            if bars_collected > 0:
                break
            print(f"    Retry collection ({attempt + 1}/{self.MAX_RETRIES})")
            self.humanizer.tick_delay()

        if bars_collected > 0:
            self.stats.add_bars(bars_collected)
            print(f"    Collected {bars_collected} bars!")
            self._consecutive_errors = 0
        else:
            # Could not collect — might be empty or wrong state
            self._error("Could not collect bars")

        self.state = BotState.WALKING_TO_BANK

    def _handle_walk_to_bank(self):
        """Walk from dispenser/conveyor back to bank."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to bank...")
        self.furnace.walk_to_bank()
        self.humanizer.action_delay()
        self.state = BotState.BANKING

    def _error(self, msg):
        """Handle a non-fatal error."""
        self._consecutive_errors += 1
        self.stats.add_error()
        print(f"  [ERROR] {msg} (errors: {self._consecutive_errors})")
