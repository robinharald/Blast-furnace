"""
Main bot state machine.

Uses the "priming" pattern for maximum efficiency:
- First trip: deposit ore, walk to dispenser, wait, collect (slow — primes the system)
- All subsequent ore trips: collect PREVIOUS batch at dispenser first,
  then walk to conveyor and deposit new ore. By the time we bank + return
  to conveyor, the new batch is already done smelting.

This eliminates smelting wait time on all trips after the first.

Coal-only trips skip the dispenser entirely (no bars produced).

State flow (after priming):
  BANKING → WALKING_TO_CONVEYOR → DEPOSITING_ORE
                                       │
                            ┌──────────┴───────────┐
                            │                      │
                       coal-only trip          ore trip
                            │                      │
                      WALKING_TO_BANK    WALKING_TO_BANK
                            │                      │
                         BANKING               BANKING
                                                   │
                                        (next ore trip starts with
                                         collecting previous bars)

Key invariants:
- Coal MUST be in the furnace before ore (prevents wrong bars)
- Bar dispenser only clickable in Hot/Cooled state (not Empty/Pouring)
- Coal bag is never banked (locked slot, shift-click to empty at conveyor)
- Goldsmith gauntlets equipped BEFORE depositing gold ore
- Ice gloves equipped BEFORE clicking bar dispenser
- First ore trip for coal bars must preload coal (no ore without coal)
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
    Core bot loop with priming pattern for maximum efficiency.
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
            use_goldsmith=(settings.use_goldsmith_gauntlets
                           and settings.bar_type == BarType.GOLD)
        )

        self.state = BotState.STARTING
        self._consecutive_errors = 0
        self._running = True

        # Trip tracking
        self._is_ore_trip = True
        self._items_withdrawn_count = 0

        # Whether bars from a previous ore trip are sitting in the dispenser
        self._bars_pending_collection = False

    def run(self):
        """Main loop."""
        bar = self.settings.bar_type
        print(f"\n  Starting Blast Furnace Bot")
        print(f"  Bar type: {bar.data.name}")
        coal_info = (f"Yes (slot {self.settings.coal_bag_slot})"
                     if self.settings.use_coal_bag else "No")
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

                self.humanizer.maybe_micro_break()
                self.humanizer.maybe_mouse_drift()

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
        """Signal graceful stop."""
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
        1. Ensure run is on
        2. If bars are pending from previous ore trip, collect them FIRST
           (walk to dispenser → collect → walk back to bank)
        3. Open bank
        4. Check supplies
        5. Deposit inventory (bars + leftover items, except coal bag)
        6. Drink stamina if needed
        7. Withdraw ores/coal
        8. Close bank
        9. Equip gloves
        10. Walk to conveyor
        """
        print(f"  [{self.stats.elapsed_formatted}] Banking... "
              f"{self.stats.status_line()}")

        self.furnace.ensure_run_enabled()

        # ── Collect pending bars from previous trip ──
        # The priming pattern: after the first ore trip, we always have
        # bars sitting in the dispenser. Collect them before banking.
        if self._bars_pending_collection:
            print(f"  [{self.stats.elapsed_formatted}] Collecting previous bars first...")

            # Equip ice gloves before going to dispenser
            if self.settings.use_ice_gloves:
                self.furnace.swap_to_ice_gloves()

            self.furnace.walk_to_dispenser()
            self.humanizer.action_delay()

            # Bars should be ready by now (smelted while we were banking)
            # Small wait just in case
            self.furnace.wait_for_bars(timeout=2.0)

            bars_collected = 0
            for attempt in range(self.MAX_RETRIES):
                bars_collected = self.furnace.collect_bars(self.settings.bar_type)
                if bars_collected > 0:
                    break
                self.humanizer.tick_delay()

            if bars_collected > 0:
                self.stats.add_bars(bars_collected)
                print(f"    Collected {bars_collected} bars from previous batch!")
            else:
                print("    No bars to collect (may have been empty)")

            self._bars_pending_collection = False

            # Walk back to bank
            self.furnace.walk_to_bank()
            self.humanizer.action_delay()

        # ── Open bank ──
        for attempt in range(self.MAX_RETRIES):
            if self.bank.open_bank():
                break
            print(f"    Retry opening bank ({attempt + 1}/{self.MAX_RETRIES})")
            self.humanizer.transition_delay()
        else:
            self._error("Failed to open bank")
            self.state = BotState.WALKING_TO_BANK
            return

        # ── Check supplies ──
        if not self.bank.has_supplies(self.settings.bar_type):
            print("  [DONE] Out of supplies!")
            self.state = BotState.STOPPED
            return

        # ── Deposit inventory ──
        self.bank.deposit_all_except_coal_bag()
        self.humanizer.bank_delay()

        # ── Stamina ──
        if self.settings.use_stamina:
            self.bank.handle_stamina()

        # ── Withdraw ores/coal ──
        if not self.bank.withdraw_ore(self.settings.bar_type):
            self._error("Failed to withdraw ores")
            return

        # Read trip type
        self._is_ore_trip = self.bank.is_ore_trip()

        # Count items for stats
        coal_bag_slot = (self.coal_bag.get_locked_slot()
                         if self.coal_bag else None)
        self._items_withdrawn_count = self.inventory.count_filled_slots(
            exclude_slot=coal_bag_slot
        )

        # ── Close bank ──
        self.bank.close_bank()
        self.humanizer.transition_delay()

        # ── Equip correct gloves ──
        bar = self.settings.bar_type
        if bar == BarType.GOLD and self.settings.use_goldsmith_gauntlets:
            self.furnace.swap_to_goldsmith_gauntlets()

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
        Coal bag handling and deposit order managed by FurnaceHandler.
        """
        trip_type = "ore" if self._is_ore_trip else "coal"
        print(f"  [{self.stats.elapsed_formatted}] Depositing on conveyor "
              f"({trip_type} trip)...")

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

        # ── Track resource usage ──
        if self._is_ore_trip:
            self.stats.add_ore(self._items_withdrawn_count)
            if (self.settings.bar_type.data.requires_coal
                    and self.coal_bag is not None):
                self.stats.add_coal(27)
        else:
            self.stats.add_coal(self._items_withdrawn_count)
            if self.coal_bag is not None:
                self.stats.add_coal(27)

        self._consecutive_errors = 0

        # ── Route to next state ──
        if self._is_ore_trip:
            if not self.furnace.is_primed:
                # FIRST ORE TRIP: must wait for bars (no previous batch)
                self.furnace.mark_primed()
                self.state = BotState.WALKING_TO_DISPENSER
            else:
                # PRIMED: bars will smelt while we bank. Mark for collection
                # on next banking cycle. Go straight to bank.
                self._bars_pending_collection = True
                self.state = BotState.WALKING_TO_BANK
        else:
            # Coal-only trip: no bars produced, go back for more
            self.state = BotState.WALKING_TO_BANK

    def _handle_walk_to_dispenser(self):
        """Walk from conveyor to bar dispenser (first trip only)."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to dispenser "
              f"(first trip — priming)...")
        self.furnace.walk_to_dispenser()
        self.humanizer.action_delay()
        self.state = BotState.WAITING_FOR_BARS

    def _handle_waiting_for_bars(self):
        """
        Wait for bars to finish smelting (first trip only).
        The dispenser is clickable but has no bars until smelting completes.
        We wait, then attempt collection.
        """
        print(f"  [{self.stats.elapsed_formatted}] Waiting for bars to smelt...")

        # Wait at least 2 game ticks (~1.2s)
        self.humanizer.tick_delay()
        self.humanizer.tick_delay()

        # Poll for bars
        bars_ready = self.furnace.wait_for_bars(
            timeout=self.settings.smelt_wait_ms / 1000.0
        )

        if not bars_ready:
            print("    Bar detection uncertain, attempting collection anyway...")

        self.state = BotState.COLLECTING_BARS

    def _handle_collect_bars(self):
        """
        Collect bars from dispenser (first trip only — after that,
        collection happens at start of BANKING state).
        """
        print(f"  [{self.stats.elapsed_formatted}] Collecting bars...")

        # Equip ice gloves BEFORE clicking dispenser
        if self.settings.use_ice_gloves:
            self.furnace.swap_to_ice_gloves()

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
        """Walk back to bank."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to bank...")
        self.furnace.walk_to_bank()
        self.humanizer.action_delay()
        self.state = BotState.BANKING

    def _error(self, msg):
        """Handle a non-fatal error."""
        self._consecutive_errors += 1
        self.stats.add_error()
        print(f"  [ERROR] {msg} (errors: {self._consecutive_errors})")
