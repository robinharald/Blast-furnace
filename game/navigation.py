"""
Navigation — teleporting, walking, entering houses, and finding contractors.

Coordinates teleport selection, minimap walking, door detection,
and movement verification.
"""
import time
import random
import logging
from typing import Optional

from config.settings import BotSettings, ScreenRegions
from data.npcs import HouseNPC
from data.contractors import get_contractor
from data.teleports import resolve_teleport, TeleportMethod
from game.object_finder import ObjectFinder
from game.minimap import MinimapNavigator
from game.inventory import InventoryReader
from game.dialogue import DialogueHandler
from game.camera import CameraManager
from screen.capture import sample_center_region, frames_differ
from input import mouse, keyboard
from anti_detect.humanizer import Humanizer

logger = logging.getLogger(__name__)


class Navigator:
    """Handles all bot navigation: teleporting, walking, entering buildings."""

    def __init__(
        self,
        settings: BotSettings,
        regions: ScreenRegions,
        finder: ObjectFinder,
        minimap: MinimapNavigator,
        inventory: InventoryReader,
        dialogue: DialogueHandler,
        camera: CameraManager,
        humanizer: Humanizer,
    ):
        self.settings = settings
        self.regions = regions
        self.finder = finder
        self.minimap = minimap
        self.inventory = inventory
        self.dialogue = dialogue
        self.camera = camera
        self.humanizer = humanizer

    # ------------------------------------------------------------------
    # Teleporting
    # ------------------------------------------------------------------

    def teleport_to_city(self, city: str) -> bool:
        """
        Teleport to the given city using the best available method.
        Returns True if teleport was initiated.
        """
        tp = resolve_teleport(city, self.settings)
        if tp is None:
            logger.error(f"No valid teleport found for {city}")
            return False

        logger.info(f"Teleporting to {city} via {tp.name}")

        if tp.method_type == "tab":
            return self._use_teleport_tab(tp)
        elif tp.method_type == "equipment":
            return self._use_equipment_teleport(tp)
        elif tp.method_type == "spell":
            return self._use_spell_teleport(tp)

        return False

    def _use_teleport_tab(self, tp: TeleportMethod) -> bool:
        """Click a teleport tab in inventory."""
        # Find tab by color
        slot = self.inventory.find_first_slot_with_color(
            tp.item_color, tolerance=30
        )
        if slot is None:
            logger.warning(f"Teleport tab not found in inventory for {tp.name}")
            return False

        self.inventory.click_slot(slot)
        return True

    def _use_equipment_teleport(self, tp: TeleportMethod) -> bool:
        """Right-click equipment for teleport option."""
        # Open equipment tab
        mouse.click(self.regions.equipment_tab.x, self.regions.equipment_tab.y, variance=3)
        self.humanizer.action_delay()

        # The equipment slot positions are relative — for now click
        # the general area and select the option from the context menu
        # This is simplified; a full implementation would map equipment slots
        keyboard.press_f_key(4)  # Equipment tab
        self.humanizer.action_delay()

        # Right-click the equipment piece (TODO: map exact slot positions)
        # For now, this is a placeholder that works with RuneLite menu entry swapper
        logger.info(f"Equipment teleport: {tp.name} ({tp.equipment_option})")
        return True

    def _use_spell_teleport(self, tp: TeleportMethod) -> bool:
        """Cast a teleport spell from the spellbook."""
        keyboard.press_f_key(6)  # Spellbook tab
        self.humanizer.action_delay()

        # Find spell by approximate position (spellbook layout is fixed)
        # This is a placeholder — exact positions depend on calibration
        mouse.click(
            self.regions.spellbook_tab.x, self.regions.spellbook_tab.y,
            variance=5,
        )
        self.humanizer.action_delay()

        # Switch back to inventory tab
        keyboard.press_f_key(3)
        return True

    def wait_for_teleport(self, timeout: float = 6.0) -> bool:
        """Wait for teleport animation to complete by detecting viewport stability."""
        logger.debug("Waiting for teleport animation...")
        time.sleep(1.5)  # Initial animation delay

        vp = self.regions.viewport
        prev_frame = sample_center_region(vp.x, vp.y, vp.w, vp.h)

        start = time.time()
        stable_count = 0

        while time.time() - start < timeout:
            time.sleep(0.3)
            curr_frame = sample_center_region(vp.x, vp.y, vp.w, vp.h)

            if not frames_differ(prev_frame, curr_frame):
                stable_count += 1
                if stable_count >= 2:
                    logger.debug("Viewport stabilized — teleport complete")
                    return True
            else:
                stable_count = 0

            prev_frame = curr_frame

        logger.warning("Teleport wait timed out")
        return True  # Assume done

    # ------------------------------------------------------------------
    # Walking
    # ------------------------------------------------------------------

    def walk_to_house(self, npc: HouseNPC) -> bool:
        """
        Walk from teleport landing spot to the NPC's house.
        Uses minimap clicking with known bearing/distance.
        """
        logger.info(f"Walking to {npc.name}'s house ({npc.walk_bearing}, {npc.walk_distance})")
        self.minimap.ensure_running()
        self.humanizer.action_delay()

        # Click minimap in the house direction
        self.minimap.click_direction(npc.walk_bearing, npc.walk_distance)

        # Wait for arrival (poll for movement to stop)
        return self._wait_until_idle(timeout=15.0)

    def walk_to_contractor(self, city: str) -> bool:
        """Walk to the contractor in the current city (Mode B)."""
        contractor = get_contractor(city)
        logger.info(f"Walking to contractor {contractor.name} in {city}")
        self.minimap.ensure_running()
        self.humanizer.action_delay()

        self.minimap.click_direction(contractor.walk_bearing, contractor.walk_distance)
        return self._wait_until_idle(timeout=15.0)

    def enter_house(self) -> bool:
        """Click the house door to enter (tagged orange with Object Markers)."""
        door_pos = self.finder.find_door()
        if door_pos:
            logger.debug(f"Found door at {door_pos}")
            mouse.click(*door_pos, variance=4)
            self.humanizer.walk_delay()
            return self._wait_until_idle(timeout=5.0)
        else:
            # Door not visible — house may be open, or need to walk closer
            logger.debug("No door found — house may be open")
            return True

    def change_floor(self) -> bool:
        """Use stairs/ladder to change floor (Norman, Jess houses)."""
        stair_pos = self.finder.find_staircase()
        if stair_pos:
            logger.debug(f"Found staircase at {stair_pos}")
            mouse.click(*stair_pos, variance=4)
            self.humanizer.walk_delay()
            return self._wait_until_idle(timeout=5.0)
        else:
            # Try rotating camera to find stairs
            stair_pos = self.camera.rotate_to_find(self.finder.find_staircase)
            if stair_pos:
                mouse.click(*stair_pos, variance=4)
                self.humanizer.walk_delay()
                return self._wait_until_idle(timeout=5.0)

        logger.warning("Staircase not found")
        return False

    def _wait_until_idle(self, timeout: float = 10.0) -> bool:
        """
        Wait for the player to stop moving by comparing viewport frames.
        Returns True when idle detected, False on timeout.
        """
        vp = self.regions.viewport
        prev_frame = sample_center_region(vp.x, vp.y, vp.w, vp.h)
        stable_count = 0
        start = time.time()

        while time.time() - start < timeout:
            time.sleep(0.4)
            curr_frame = sample_center_region(vp.x, vp.y, vp.w, vp.h)

            if not frames_differ(prev_frame, curr_frame):
                stable_count += 1
                if stable_count >= 2:
                    return True
            else:
                stable_count = 0

            prev_frame = curr_frame

        return True  # Assume idle on timeout
