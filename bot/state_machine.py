"""
Main bot loop — state machine with handler dispatch.

Supports two operating modes:
- Mode A: NPC Contact (Lunar spellbook)
- Mode B: Walk-to-Contractor (no spellbook requirement)

Each tick: check breaks -> dispatch handler -> check errors -> repeat.
"""
import time
import logging
from typing import Optional, Callable

import keyboard as kb_module

from bot.states import BotState
from bot.session import SessionStats
from bot.error_recovery import ErrorRecovery
from config.settings import BotSettings, ScreenRegions
from anti_detect.session_profile import SessionProfile
from anti_detect.humanizer import Humanizer
from anti_detect.attention_sim import AttentionSimulator
from game.object_finder import ObjectFinder
from game.inventory import InventoryReader
from game.camera import CameraManager
from game.dialogue import DialogueHandler
from game.minimap import MinimapNavigator
from game.run_energy import RunEnergyMonitor
from game.contract import ContractManager
from game.navigation import Navigator
from game.house_worker import HouseWorker
from game.bank import BankHandler
from game.spellbook import SpellCaster
from data.materials import get_tier

logger = logging.getLogger(__name__)


class MahoganyHomesBot:
    """
    The main bot — state machine that drives all game interaction.
    """

    def __init__(
        self,
        settings: BotSettings,
        regions: ScreenRegions,
        log_callback: Optional[Callable] = None,
    ):
        self.settings = settings
        self.regions = regions
        self.log_callback = log_callback

        # State
        self.state = BotState.STARTING
        self._running = False
        self._paused = False

        # Session profile & anti-detection
        self.profile = SessionProfile()
        self.humanizer = Humanizer(self.profile)
        self.attention = AttentionSimulator(self.profile, regions)

        # Game modules
        vp = (regions.viewport.x, regions.viewport.y,
              regions.viewport.w, regions.viewport.h)
        self.finder = ObjectFinder(vp)
        self.inventory = InventoryReader(regions)
        self.camera = CameraManager()
        self.dialogue = DialogueHandler(regions)
        self.minimap = MinimapNavigator(regions)
        self.run_energy = RunEnergyMonitor(regions, self.profile.tea_threshold)
        self.contract = ContractManager(regions, settings.tier)
        self.navigator = Navigator(
            settings, regions, self.finder, self.minimap,
            self.inventory, self.dialogue, self.camera, self.humanizer,
        )
        self.worker = HouseWorker(
            self.finder, self.camera, self.humanizer, self.attention, vp,
        )
        self.bank = BankHandler(
            settings, regions, self.finder, self.inventory, self.humanizer,
        )
        self.spellcaster = SpellCaster(regions, self.humanizer)

        # Tracking
        self.stats = SessionStats()
        self.recovery = ErrorRecovery()
        self.tier_data = get_tier(settings.tier)

        # Hotspot tracking for current contract
        self._current_hotspots = []

    def _log(self, msg: str) -> None:
        logger.info(msg)
        if self.log_callback:
            self.log_callback(msg)

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the bot loop."""
        self._running = True
        self._paused = False
        self.state = BotState.STARTING
        self._log(f"Bot started | {self.profile}")
        self._log(f"Mode: {self.settings.mode} | Tier: {self.settings.tier}")

        # Register stop key
        kb_module.on_press_key(self.settings.stop_key, lambda _: self.stop())

        try:
            while self._running:
                if self._paused:
                    time.sleep(0.5)
                    continue

                if self.state == BotState.STOPPED:
                    break

                # Check session timeout
                if self.humanizer.should_stop_session():
                    self._log("Session time reached — stopping")
                    self.state = BotState.STOPPED
                    break

                # Check for planned breaks
                self.humanizer.check_and_take_break()

                # Dispatch to handler
                self._tick()

                # Check for micro-breaks between ticks
                self.humanizer.check_micro_break()

        except Exception as e:
            logger.exception(f"Bot crashed: {e}")
            self._log(f"ERROR: {e}")
        finally:
            self._running = False
            self._log(f"Bot stopped | {self.stats.summary()}")

    def stop(self) -> None:
        """Gracefully stop the bot."""
        self._log("Stop requested")
        self._running = False
        self.state = BotState.STOPPED

    def pause(self) -> None:
        self._paused = not self._paused
        self._log(f"Bot {'paused' if self._paused else 'resumed'}")

    @property
    def is_running(self) -> bool:
        return self._running and self.state != BotState.STOPPED

    # ------------------------------------------------------------------
    # Tick Dispatch
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Dispatch to the handler for the current state."""
        handlers = {
            BotState.STARTING: self._handle_starting,
            BotState.BANKING: self._handle_banking,
            BotState.CASTING_NPC_CONTACT: self._handle_casting_npc_contact,
            BotState.WALKING_TO_CONTRACTOR: self._handle_walking_to_contractor,
            BotState.TALKING_TO_CONTRACTOR: self._handle_talking_to_contractor,
            BotState.SELECTING_TIER: self._handle_selecting_tier,
            BotState.SELECTING_TIER_CONTRACTOR: self._handle_selecting_tier,
            BotState.PARSING_CONTRACT: self._handle_parsing_contract,
            BotState.TELEPORTING: self._handle_teleporting,
            BotState.WAITING_FOR_TELEPORT: self._handle_waiting_for_teleport,
            BotState.WALKING_TO_HOUSE: self._handle_walking_to_house,
            BotState.ENTERING_HOUSE: self._handle_entering_house,
            BotState.SCANNING_HOTSPOTS: self._handle_scanning_hotspots,
            BotState.INTERACTING_HOTSPOT: self._handle_interacting_hotspot,
            BotState.WAITING_FOR_BUILD: self._handle_waiting_for_build,
            BotState.CHANGING_FLOOR: self._handle_changing_floor,
            BotState.TALKING_TO_HOMEOWNER: self._handle_talking_to_homeowner,
            BotState.HANDLING_COMPLETION_DIALOGUE: self._handle_completion_dialogue,
            BotState.RECOVERING: self._handle_recovering,
        }

        handler = handlers.get(self.state)
        if handler:
            try:
                handler()
                self.recovery.record_success()
            except Exception as e:
                logger.error(f"Handler error in {self.state.name}: {e}")
                self.recovery.record_error(self.state, str(e))
                self.stats.record_error()
                if self.recovery.should_stop():
                    self._log("Too many errors — stopping bot")
                    self.state = BotState.STOPPED
                else:
                    self.state = BotState.RECOVERING
        else:
            logger.warning(f"No handler for state {self.state}")
            self.state = BotState.RECOVERING

    # ------------------------------------------------------------------
    # State Handlers
    # ------------------------------------------------------------------

    def _handle_starting(self) -> None:
        self._log("Initializing...")
        self.humanizer.transition_delay()
        # Start with banking to ensure we have supplies
        self.state = BotState.BANKING

    def _handle_banking(self) -> None:
        self._log("Banking...")
        self.finder.clear_cache()
        success = self.bank.full_bank_sequence()
        self.stats.record_bank_trip()

        if success:
            if self.contract.has_active_contract:
                # Already have a contract — go do it
                self.state = BotState.TELEPORTING
            elif self.settings.mode == "npc_contact":
                self.state = BotState.CASTING_NPC_CONTACT
            else:
                self.state = BotState.WALKING_TO_CONTRACTOR
        else:
            self.recovery.record_error(self.state, "banking_failed")
            self.state = BotState.RECOVERING

    def _handle_casting_npc_contact(self) -> None:
        self._log("Casting NPC Contact...")
        success = self.spellcaster.cast_npc_contact()
        if success:
            self.humanizer.reaction_delay()
            self.state = BotState.SELECTING_TIER
        else:
            self.recovery.record_error(self.state, "npc_contact_failed")
            self.state = BotState.RECOVERING

    def _handle_walking_to_contractor(self) -> None:
        city = self.contract.current_city or "falador"
        self._log(f"Walking to contractor in {city}...")
        self.navigator.walk_to_contractor(city)
        self.humanizer.walk_delay()
        self.state = BotState.TALKING_TO_CONTRACTOR

    def _handle_talking_to_contractor(self) -> None:
        self._log("Talking to contractor...")
        contractor_pos = self.finder.find_contractor_npc()
        if contractor_pos:
            from input import mouse
            mouse.click(*contractor_pos, variance=4)
            self.humanizer.reaction_delay()
            self.dialogue.wait_for_dialogue(timeout=5.0)
            self.state = BotState.SELECTING_TIER_CONTRACTOR
        else:
            self.recovery.record_error(self.state, "contractor_not_found")
            self.state = BotState.RECOVERING

    def _handle_selecting_tier(self) -> None:
        self._log(f"Selecting tier: {self.settings.tier}...")
        self.dialogue.handle_tier_selection(self.settings.tier)
        self.humanizer.action_delay()

        # Advance through remaining dialogue
        self.dialogue.handle_contract_dialogue()
        self.state = BotState.PARSING_CONTRACT

    def _handle_parsing_contract(self) -> None:
        self._log("Parsing contract assignment...")
        self.humanizer.reaction_delay()

        npc_name = self.contract.parse_contract_from_chat()
        if npc_name:
            self._log(f"Contract: {npc_name} in {self.contract.current_city}")
            self.finder.clear_cache()

            # Check if we need to bank
            plank_count = self.inventory.count_planks(
                self.tier_data.plank_color, self.tier_data.plank_tolerance
            )
            if plank_count < self.tier_data.max_planks_per_contract:
                self.state = BotState.BANKING
            else:
                self.state = BotState.TELEPORTING
        else:
            self._log("Failed to parse contract — retrying...")
            self.humanizer.action_delay()
            # Try again after a brief wait
            self.recovery.record_error(self.state, "parse_failed")
            self.state = BotState.RECOVERING

    def _handle_teleporting(self) -> None:
        city = self.contract.current_city
        self._log(f"Teleporting to {city}...")
        success = self.navigator.teleport_to_city(city)
        if success:
            self.state = BotState.WAITING_FOR_TELEPORT
        else:
            self.recovery.record_error(self.state, "teleport_failed")
            self.state = BotState.RECOVERING

    def _handle_waiting_for_teleport(self) -> None:
        self.navigator.wait_for_teleport()
        self.finder.clear_cache()
        self.state = BotState.WALKING_TO_HOUSE

    def _handle_walking_to_house(self) -> None:
        npc = self.contract.current_npc
        self._log(f"Walking to {npc.name}'s house...")
        self.navigator.walk_to_house(npc)
        self.humanizer.walk_delay()
        self.state = BotState.ENTERING_HOUSE

    def _handle_entering_house(self) -> None:
        self._log("Entering house...")
        self.navigator.enter_house()
        self.humanizer.transition_delay()
        self.state = BotState.SCANNING_HOTSPOTS

    def _handle_scanning_hotspots(self) -> None:
        hotspots = self.worker.find_hotspots_with_camera()

        if hotspots:
            target = self.attention.pick_hotspot(hotspots)
            self._current_hotspots = hotspots
            self._log(f"Found {len(hotspots)} hotspots")
            # Go directly to interacting
            self.worker.interact_with_hotspot(target)
            self.state = BotState.WAITING_FOR_BUILD
        elif self.contract.needs_upstairs:
            self._log("No hotspots on this floor — changing floor")
            self.state = BotState.CHANGING_FLOOR
        else:
            self._log("All hotspots complete — talking to homeowner")
            self.state = BotState.TALKING_TO_HOMEOWNER

    def _handle_interacting_hotspot(self) -> None:
        # This state is mostly handled inline in scanning
        self.state = BotState.WAITING_FOR_BUILD

    def _handle_waiting_for_build(self) -> None:
        self.worker.wait_for_build()
        self.stats.record_hotspot()
        self.contract.mark_hotspot_done()

        # Maybe do a human thing between hotspots
        self.attention.maybe_do_human_thing()

        # Scan for next hotspot
        self.state = BotState.SCANNING_HOTSPOTS

    def _handle_changing_floor(self) -> None:
        self._log("Changing floor...")
        success = self.navigator.change_floor()
        self.contract.state.visited_upstairs = True
        if success:
            self.humanizer.walk_delay()
            self.state = BotState.SCANNING_HOTSPOTS
        else:
            self.recovery.record_error(self.state, "floor_change_failed")
            self.state = BotState.RECOVERING

    def _handle_talking_to_homeowner(self) -> None:
        self._log("Talking to homeowner...")
        npc_pos = self.finder.find_homeowner_npc()

        if npc_pos is None:
            # Try rotating camera to find NPC
            npc_pos = self.camera.rotate_to_find(self.finder.find_homeowner_npc)

        if npc_pos:
            from input import mouse
            # Maybe double-click (imperfection)
            if self.attention.profile.should_double_click():
                mouse.double_click(*npc_pos, variance=4)
            else:
                mouse.click(*npc_pos, variance=4)

            self.humanizer.reaction_delay()
            self.dialogue.wait_for_dialogue(timeout=5.0)
            self.state = BotState.HANDLING_COMPLETION_DIALOGUE
        else:
            self.recovery.record_error(self.state, "homeowner_not_found")
            self.state = BotState.RECOVERING

    def _handle_completion_dialogue(self) -> None:
        accept_tea = self.run_energy.should_accept_tea()
        self._log(f"Completing contract (tea: {'yes' if accept_tea else 'no'})...")

        self.dialogue.handle_completion_dialogue(accept_tea=accept_tea)
        self.humanizer.transition_delay()

        # Record completion
        self.contract.mark_complete()
        self.stats.record_contract(self.tier_data.avg_xp_per_contract,
                                    self.tier_data.points_per_contract)
        self._log(f"Contract complete! {self.stats.summary()}")

        # Attention: maybe do a human thing after completion
        self.attention.maybe_do_human_thing()

        # Decide next action
        self._decide_next_action()

    def _decide_next_action(self) -> None:
        """After completing a contract, decide what to do next."""
        # Check supplies
        plank_count = self.inventory.count_planks(
            self.tier_data.plank_color, self.tier_data.plank_tolerance
        )
        needs_bank = plank_count < self.tier_data.max_planks_per_contract

        if needs_bank:
            self._log("Low on supplies — banking")
            self.state = BotState.BANKING
        elif self.settings.mode == "npc_contact":
            self.state = BotState.CASTING_NPC_CONTACT
        else:
            # Mode B: walk to contractor in same city
            self.state = BotState.WALKING_TO_CONTRACTOR

    def _handle_recovering(self) -> None:
        action = self.recovery.get_recovery_action(self.state)
        self._log(f"Recovering: {action}")

        if action == "retry":
            # Go back to the state that failed
            self.humanizer.transition_delay()
            # Default: go to scanning hotspots if in a house, else banking
            if self.contract.has_active_contract:
                self.state = BotState.SCANNING_HOTSPOTS
            else:
                self.state = BotState.BANKING

        elif action == "reorient":
            self.camera.rotate_90()
            self.humanizer.transition_delay()
            self.state = BotState.SCANNING_HOTSPOTS

        elif action == "relocate":
            self._log("Relocating to bank...")
            self.state = BotState.BANKING

        elif action == "abandon":
            self._log("Abandoning contract...")
            self.contract.state.reset()
            self.state = BotState.BANKING

        elif action == "stop":
            self.state = BotState.STOPPED
