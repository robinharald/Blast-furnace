"""
Main bot state machine.

Uses the "priming" pattern for maximum efficiency:
- First trip: deposit ore → walk to dispenser → wait → collect bars (slow — primes the system)
- All subsequent ore trips: deposit ore on conveyor (empties inventory) →
  walk to dispenser → collect PREVIOUS bars → walk to bank.
  By the time we bank + walk back, the new batch is already done smelting.

This eliminates smelting wait time on all trips after the first.

Coal-only trips skip the dispenser entirely (no bars produced).

State flow (after priming):
  BANKING → WALKING_TO_CONVEYOR → DEPOSITING_ORE
                                       │
                            ┌──────────┴───────────┐
                            │                      │
                       coal-only trip          ore trip
                            │                      │
                      WALKING_TO_BANK   COLLECTING_PREVIOUS_BARS
                            │                      │
                         BANKING            WALKING_TO_BANK
                                                   │
                                                BANKING

Key: depositing FIRST (frees inventory), THEN collecting bars (fills inventory
with bars from previous trip). Zero idle time after priming.

Key invariants:
- Coal MUST be in the furnace before ore (prevents wrong bars)
- Coal bag is never banked (locked slot, left-click to empty at conveyor)
- Goldsmith gauntlets equipped BEFORE depositing gold ore
- Ice gloves equipped BEFORE clicking bar dispenser
- First ore trip for coal bars must preload coal (no ore without coal)
- Bar dispenser doesn't work while a dialogue box is open — dismiss first
"""

import time
import pyautogui
import keyboard

from bot.states import BotState
from bot.session import SessionStats
from config import ScreenRegions, BotSettings
from game.inventory import InventoryReader
from game.coal_bag import CoalBagManager
from game.bank import BankHandler
from game.furnace import FurnaceHandler
from input import mouse
from anti_detect.humanizer import Humanizer
from data.bars import BarType


class BlastFurnaceStateMachine:
    """
    Core bot loop with priming pattern for maximum efficiency.

    After priming, the loop is:
      Bank → Walk to conveyor → Deposit ore → Collect previous bars → Walk to bank
    This ensures zero idle time waiting for bars to smelt.
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
                # Recovery: try to get back to bank
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
            BotState.COLLECTING_PREVIOUS_BARS: self._handle_collect_previous_bars,
            BotState.WALKING_TO_DISPENSER: self._handle_walk_to_dispenser,
            BotState.WAITING_FOR_BARS: self._handle_waiting_for_bars,
            BotState.COLLECTING_BARS_FIRST_TRIP: self._handle_collect_bars_first_trip,
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
        2. Open bank
        3. Check supplies
        4. Deposit inventory (bars from previous collection + leftovers, except coal bag)
        5. Drink stamina if needed
        6. Fill coal bag (if applicable)
        7. Withdraw ores/coal
        8. Close bank
        9. Equip goldsmith gauntlets (if gold)
        """
        print(f"  [{self.stats.elapsed_formatted}] Banking... "
              f"{self.stats.status_line()}")

        self.furnace.ensure_run_enabled()

        # Dismiss any stale dialogue that might be blocking
        self._dismiss_dialogue()

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

        # ── Deposit inventory (bars from previous trip + any leftovers) ──
        self.bank.deposit_all_except_locked()
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

        # ── Equip correct gloves for depositing ──
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

        After depositing, route to:
        - COLLECTING_PREVIOUS_BARS: if primed (previous bars in dispenser)
        - WALKING_TO_DISPENSER: if first ore trip (need to wait for smelt)
        - WALKING_TO_BANK: if coal-only trip (no bars to collect)
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
                # FIRST ORE TRIP: must wait for these bars (no previous batch)
                self.furnace.mark_primed()
                self.state = BotState.WALKING_TO_DISPENSER
            elif self._bars_pending_collection:
                # PRIMED: inventory is now empty after depositing.
                # Collect previous batch of bars from dispenser.
                self.state = BotState.COLLECTING_PREVIOUS_BARS
            else:
                # No pending bars (shouldn't happen after priming, but safe fallback)
                self._bars_pending_collection = True
                self.state = BotState.WALKING_TO_BANK
        else:
            # Coal-only trip: no bars produced, go back for more
            self.state = BotState.WALKING_TO_BANK

    def _handle_collect_previous_bars(self):
        """
        Collect bars from the PREVIOUS ore trip.

        We just deposited new ore on the conveyor (inventory is empty now).
        The dispenser has bars from the last ore trip that smelted while
        we were banking. Walk to dispenser, swap to ice gloves, collect.

        GOLD BAR TIMING: When using goldsmith gauntlets, we must wait for
        the XP drop (~2 game ticks after depositing) before swapping to
        ice gloves. If we swap too early, the gold ore smelts without the
        gauntlets bonus. The walk to the dispenser provides this delay naturally,
        but we add a small extra wait for safety.

        The new ore smelts while we do this + walk to bank + bank.
        """
        print(f"  [{self.stats.elapsed_formatted}] Collecting previous bars "
              f"at dispenser...")

        # Click minimap to START walking to dispenser
        mx, my = self.regions.minimap_dispenser
        mouse.click(mx, my, variance=3)

        # GLOVE SWAP WHILE RUNNING:
        # Instead of waiting until arrival, swap gloves immediately after
        # clicking minimap. Character is already moving — this uses the
        # travel time productively and looks more human than standing
        # still at the dispenser to fiddle with gear.
        #
        # GOLD BAR XP DROP TIMING:
        # Must wait for XP drop from newly deposited gold before swapping.
        # The XP drop happens ~2 ticks (1.2s) after ore reaches the melting pot.
        # The minimap click + the delay below covers this.
        if self.settings.use_ice_gloves:
            if (self.settings.bar_type == BarType.GOLD
                    and self.settings.use_goldsmith_gauntlets):
                # Wait ~2 ticks for XP drop before swapping off goldsmith
                self.humanizer.tick_delay()
                self.humanizer.tick_delay()
            self.furnace.swap_to_ice_gloves()

        # Now wait for arrival at dispenser
        self.furnace._wait_until_idle(timeout=6.0)
        self.humanizer.action_delay()

        # Bars should be ready by now (smelted during our bank trip)
        # Small safety wait
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
            self._consecutive_errors = 0
        else:
            print("    No bars to collect (may have been empty)")

        # After collecting, swap back to goldsmith if needed.
        # Trick: clicking goldsmith in inventory auto-dismisses any
        # remaining dispenser message, saving a tick.
        if (self.settings.bar_type == BarType.GOLD
                and self.settings.use_goldsmith_gauntlets):
            self.furnace.swap_to_goldsmith_gauntlets()

        # Mark that we've collected; new bars will be ready after this trip's ore smelts
        self._bars_pending_collection = True  # New ore is smelting → bars pending next time

        self.state = BotState.WALKING_TO_BANK

    def _handle_walk_to_dispenser(self):
        """Walk from conveyor to bar dispenser (first trip only)."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to dispenser "
              f"(first trip — priming)...")

        # Click minimap to start walking
        mx, my = self.regions.minimap_dispenser
        mouse.click(mx, my, variance=3)

        # Swap gloves while running (same optimization as collect_previous_bars)
        if self.settings.use_ice_gloves:
            if (self.settings.bar_type == BarType.GOLD
                    and self.settings.use_goldsmith_gauntlets):
                self.humanizer.tick_delay()
                self.humanizer.tick_delay()
            self.furnace.swap_to_ice_gloves()

        # Wait for arrival
        self.furnace._wait_until_idle(timeout=6.0)
        self.humanizer.action_delay()
        self.state = BotState.WAITING_FOR_BARS

    def _handle_waiting_for_bars(self):
        """
        Wait for bars to finish smelting (first trip only).
        We wait here because there are no previous bars to collect.
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

        self.state = BotState.COLLECTING_BARS_FIRST_TRIP

    def _handle_collect_bars_first_trip(self):
        """
        Collect bars from dispenser (first trip only — after that,
        collection happens in COLLECTING_PREVIOUS_BARS after depositing).
        """
        print(f"  [{self.stats.elapsed_formatted}] Collecting bars (first trip)...")

        # Ice gloves already swapped during walk — no need to swap here

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

        # Swap back to goldsmith for next trip's deposit
        if (self.settings.bar_type == BarType.GOLD
                and self.settings.use_goldsmith_gauntlets):
            self.furnace.swap_to_goldsmith_gauntlets()

        # After first trip, subsequent trips will have bars pending
        self._bars_pending_collection = False  # Just collected, nothing pending yet

        self.state = BotState.WALKING_TO_BANK

    def _handle_walk_to_bank(self):
        """Walk back to bank."""
        print(f"  [{self.stats.elapsed_formatted}] Walking to bank...")
        self.furnace.walk_to_bank()
        self.humanizer.action_delay()
        self.state = BotState.BANKING

    def _dismiss_dialogue(self):
        """
        Dismiss any blocking dialogue box.

        The bar dispenser doesn't work while a dialogue is open.
        Random NPC dialogues (foreman, etc.) can appear and block actions.
        Pressing SPACE dismisses "Click here to continue" dialogues.
        Pressing ESC closes other dialogue types.
        """
        pyautogui.press("space")
        time.sleep(0.15)
        pyautogui.press("space")
        time.sleep(0.15)

    def _error(self, msg):
        """Handle a non-fatal error."""
        self._consecutive_errors += 1
        self.stats.add_error()
        print(f"  [ERROR] {msg} (errors: {self._consecutive_errors})")
