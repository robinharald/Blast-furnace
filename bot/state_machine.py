"""
Main bot state machine.

Every state transition validates prerequisites before acting.
Every click verifies its result before moving on.
Robust error recovery with retry logic.

State flow:
  BANKING → WALKING_TO_CONVEYOR → DEPOSITING_ORE
                                       │
                            ┌──────────┴───────────┐
                            │                      │
                       coal-only trip          ore trip
                            │                      │
                      WALKING_TO_BANK    WALKING_TO_DISPENSER
                            │                      │
                         BANKING          WAITING_FOR_BARS
                                                   │
                                           COLLECTING_BARS
                                                   │
                                           WALKING_TO_BANK
                                                   │
                                               BANKING

Key invariants:
- Coal MUST be in the furnace before ore for coal-requiring bars
- The bar dispenser is only clickable when bars are ready
- Coal bag is never banked (locked slot)
- Goldsmith gauntlets must be equipped BEFORE depositing gold ore
- Ice gloves must be equipped BEFORE clicking the bar dispenser
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
    The core loop. Each state:
    1. Validates preconditions
    2. Performs the action with retries
    3. Verifies the result
    4. Transitions to the next state

    Falls back to WALKING_TO_BANK on repeated failures.
    Stops after MAX_CONSECUTIVE_ERRORS.
    """

    MAX_RETRIES = 3
    MAX_CONSECUTIVE_ERRORS = 10

    def __init__(self, regions: ScreenRegions, settings: BotSettings):
        self.regions = regions
        self.settings = settings
        self.humanizer = Humanizer()

        # Build handler chain
        self.inventory = InventoryReader(regions, self.humanizer)

        if settings.use_coal_bag:
            self.coal_bag = CoalBagManager(
                settings.coal_bag_slot, regions, self.inventory, self.humanizer
            )
        else:
            self.coal_bag = None

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

        # Trip tracking
        self._is_ore_trip = True
        self._items_withdrawn_count = 0

    def run(self):
        """Main loop. Runs until stopped or fatal error."""
        print(f"\n  Starting Blast Furnace Bot")
        print(f"  Bar type: {self.settings.bar_type.data.name}")
        coal_info = f"Yes (slot {self.settings.coal_bag_slot})" if self.settings.use_coal_bag else "No"
        print(f"  Coal bag: {coal_info}")
        print(f"  Stamina:  {'Yes' if self.settings.use_stamina else 'No'}")
        print(f"  Stop key: {self.settings.stop_key.upper()}")
        print(f"  Press {self.settings.stop_key.upper()} at any time to stop.\n")

        keyboard.on_press_key(self.settings.stop_key, lambda _: self.stop())

        self.state = BotState.BANKING

        while self._running and self.state != BotState.STOPPED:
            try:
                self._tick()

                if self._consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                    print(f"\n  [ERROR] Too many consecutive errors "
                          f"({self._consecutive_errors}). Stopping.")
                    self.state = BotState.STOPPED
                    break

                # Anti-detection: occasional micro-breaks and mouse drift
                self.humanizer.maybe_micro_break()
                self.humanizer.maybe_mouse_drift()

                # Periodic long AFK breaks
                if self.humanizer.should_take_break():
                    print("  [BREAK] Taking a short break...")
                    self.stats.breaks_taken += 1
                    self.humanizer.take_long_break()
                    print("  [BREAK] Resuming.")

            except KeyboardInterrupt:
                print("\n  Interrupted by user.")
                self.state = BotState.STOPPED
            except Exception as e:
                print(f"  [ERROR] Unexpected: {e}")
                self._consecutive_errors += 1
                self.stats.add_error()
                self.humanizer.transition_delay()
                self.state = BotState.WALKING_TO_BANK

        keyboard.unhook_all()
        print(self.stats.summary())

    def stop(self):
        """Signal the bot to stop gracefully."""
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
        1. Ensure run is enabled
        2. Open bank
        3. Check supplies exist
        4. Deposit inventory (except coal bag)
        5. Drink stamina if needed
        6. Withdraw ores/coal for next trip
        7. Close bank
        8. Equip correct gloves
        9. Transition to WALKING_TO_CONVEYOR
        """
        print(f"  [{self.stats.elapsed_formatted}] Banking... "
              f"{self.stats.status_line()}")

        # Ensure run is on
        self.furnace.ensure_run_enabled()

        # Open bank with retry
        for attempt in range(self.MAX_RETRIES):
            if self.bank.open_bank():
                break
            print(f"    Retry opening bank ({attempt + 1}/{self.MAX_RETRIES})")
            self.humanizer.transition_delay()
        else:
            self._error("Failed to open bank")
            self.state = BotState.WALKING_TO_BANK
            return

        # Check supplies
        if not self.bank.has_supplies(self.settings.bar_type):
            print("  [DONE] Out of supplies!")
            self.state = BotState.STOPPED
            return

        # Deposit inventory (except coal bag)
        self.bank.deposit_all_except_coal_bag()
        self.humanizer.bank_delay()

        # Stamina management
        if self.settings.use_stamina:
            self.bank.handle_stamina()

        # Withdraw ores/coal for this trip
        if not self.bank.withdraw_ore(self.settings.bar_type):
            self._error("Failed to withdraw ores")
            return

        # Read trip type (set during withdraw_ore, before counter changed)
        self._is_ore_trip = self.bank.is_ore_trip()

        # Count items for stat tracking
        coal_bag_slot = self.coal_bag.get_locked_slot() if self.coal_bag else None
        self._items_withdrawn_count = self.inventory.count_filled_slots(
            exclude_slot=coal_bag_slot
        )

        # Close bank
        self.bank.close_bank()
        self.humanizer.transition_delay()

        # Equip correct gloves AFTER closing bank, BEFORE going to conveyor
        bar = self.settings.bar_type
        if bar == BarType.GOLD and self.settings.use_goldsmith_gauntlets:
            # Goldsmith gauntlets must be on when gold ore enters the furnace
            self.furnace.swap_to_goldsmith_gauntlets()
        elif self._is_ore_trip and self.settings.use_ice_gloves:
            # For non-gold ore trips, we'll need ice gloves at the dispenser
            # Don't swap yet — we'll swap before collection
            pass

        # Track the trip
        self.stats.add_trip()
        self._consecutive_errors = 0
        self.state = BotState.WALKING_TO_CONVEYOR

    def _handle_walk_to_conveyor(self):
        """Walk from bank to conveyor belt via minimap."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to conveyor...")
        self.furnace.walk_to_conveyor()
        self.humanizer.action_delay()
        self.state = BotState.DEPOSITING_ORE

    def _handle_deposit_ore(self):
        """
        Deposit ores on the conveyor belt.
        Coal bag emptying is handled inside FurnaceHandler based on trip type.
        """
        print(f"  [{self.stats.elapsed_formatted}] Depositing on conveyor "
              f"({'ore' if self._is_ore_trip else 'coal'} trip)...")

        for attempt in range(self.MAX_RETRIES):
            if self.furnace.deposit_on_conveyor(
                    self.settings.bar_type, self._is_ore_trip):
                break
            print(f"    Retry deposit ({attempt + 1}/{self.MAX_RETRIES})")
            self.humanizer.transition_delay()
        else:
            self._error("Failed to deposit on conveyor")
            self.state = BotState.WALKING_TO_BANK
            return

        # Track resource usage
        if self._is_ore_trip:
            self.stats.add_ore(self._items_withdrawn_count)
            # Coal bag coal was also deposited on ore trips (for coal bars)
            if (self.settings.bar_type.data.requires_coal
                    and self.coal_bag is not None):
                self.stats.add_coal(27)
        else:
            # Coal-only trip: inventory coal + coal bag coal
            self.stats.add_coal(self._items_withdrawn_count)
            if self.coal_bag is not None:
                self.stats.add_coal(27)

        self._consecutive_errors = 0

        # Route to next state
        if self._is_ore_trip:
            # Ore deposited → bars will smelt → go collect
            self.state = BotState.WALKING_TO_DISPENSER
        else:
            # Coal-only trip → go back for more
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
        Bars smelt in ~2 game ticks after ore is deposited on the conveyor.
        The dispenser is NOT interactable until bars are done.
        We must wait, not spam-click.
        """
        print(f"  [{self.stats.elapsed_formatted}] Waiting for bars...")

        # Wait at least 2 ticks (bars smelt nearly instantly at BF)
        self.humanizer.tick_delay()
        self.humanizer.tick_delay()

        # Then poll for bars with a generous timeout
        bars_ready = self.furnace.wait_for_bars(
            timeout=self.settings.smelt_wait_ms / 1000.0
        )

        if bars_ready:
            self.state = BotState.COLLECTING_BARS
        else:
            # Even if visual detection failed, bars are almost certainly
            # ready after this much waiting. Try to collect anyway.
            print("    Bar detection uncertain, attempting collection...")
            self.state = BotState.COLLECTING_BARS

    def _handle_collect_bars(self):
        """
        Collect bars from the bar dispenser.
        Must have ice gloves equipped (for non-gold, or gold if using ice gloves).
        """
        print(f"  [{self.stats.elapsed_formatted}] Collecting bars...")

        # Equip ice gloves BEFORE clicking dispenser
        if self.settings.use_ice_gloves:
            if self.settings.bar_type == BarType.GOLD:
                # For gold: swap from goldsmith gauntlets to ice gloves
                self.furnace.swap_to_ice_gloves()
            # For other bars: ice gloves should already be equipped,
            # but verify/equip just in case
            self.furnace.swap_to_ice_gloves()

        # Collect bars with retry
        bars_collected = 0
        for attempt in range(self.MAX_RETRIES):
            bars_collected = self.furnace.collect_bars(self.settings.bar_type)
            if bars_collected > 0:
                break
            print(f"    Retry collection ({attempt + 1}/{self.MAX_RETRIES})")
            self.humanizer.tick_delay()
            self.humanizer.tick_delay()

        if bars_collected > 0:
            self.stats.add_bars(bars_collected)
            print(f"    Collected {bars_collected} bars!")
            self._consecutive_errors = 0
        else:
            self._error("Could not collect bars from dispenser")

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
