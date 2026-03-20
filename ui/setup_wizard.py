"""
Setup wizard for calibrating screen positions.

Minimal calibration — only positions that can't be auto-detected.
Objects (bank, conveyor, dispenser) are found via RuneLite color markers.
Bank is closed with ESC. No minimap navigation (mass worlds are useless for that).

Saves to calibration.json.
"""

import time
import keyboard
import pyautogui
from config import ScreenRegions, save_calibration, load_calibration


def get_mouse_on_keypress(prompt, key="space"):
    """Show prompt, wait for keypress, return mouse position."""
    print(f"\n  >> {prompt}")
    print(f"     Position your mouse and press [{key.upper()}]")
    keyboard.wait(key)
    pos = pyautogui.position()
    print(f"     Captured: ({pos[0]}, {pos[1]})")
    time.sleep(0.3)  # Debounce
    return pos


def run_calibration(regions: ScreenRegions):
    """
    Interactive calibration wizard.
    Only 7 mouse positions needed (down from 15+).
    """
    print("\n" + "=" * 50)
    print("  SCREEN CALIBRATION")
    print("=" * 50)
    print("\n  Position your mouse on each element and press SPACE.")
    print("  Make sure OSRS is visible and you're at the Blast Furnace.\n")
    print("  Press ENTER to begin...")
    input()

    # ── Game viewport (2 clicks) ──
    print("\n--- GAME VIEWPORT ---")
    tl = get_mouse_on_keypress("TOP-LEFT corner of the game viewport")
    br = get_mouse_on_keypress("BOTTOM-RIGHT corner of the game viewport")
    regions.game_x = tl[0]
    regions.game_y = tl[1]
    regions.game_w = br[0] - tl[0]
    regions.game_h = br[1] - tl[1]

    # ── Inventory (2 clicks) ──
    print("\n--- INVENTORY ---")
    inv_tl = get_mouse_on_keypress("CENTER of inventory SLOT 1 (top-left slot)")
    inv_br = get_mouse_on_keypress("CENTER of inventory SLOT 28 (bottom-right slot)")
    regions.inv_slot_w = (inv_br[0] - inv_tl[0]) // (regions.inv_cols - 1)
    regions.inv_slot_h = (inv_br[1] - inv_tl[1]) // (regions.inv_rows - 1)
    regions.inv_x = inv_tl[0] - regions.inv_slot_w // 2
    regions.inv_y = inv_tl[1] - regions.inv_slot_h // 2

    # ── Bank interface (2 clicks) ──
    print("\n--- BANK INTERFACE ---")
    print("  Please OPEN YOUR BANK now.\n")
    input("  Press ENTER when the bank is open...")

    dep = get_mouse_on_keypress(
        "The 'Deposit inventory' button (backpack icon at bottom of bank)")
    regions.bank_deposit_inv_btn = (dep[0], dep[1])

    grid = get_mouse_on_keypress(
        "CENTER of the FIRST item slot in your bank tag tab (top-left slot)")
    regions.bank_grid_x = grid[0] - regions.bank_slot_w // 2
    regions.bank_grid_y = grid[1] - regions.bank_slot_h // 2

    # ── Run orb (1 click) ──
    print("\n--- RUN ORB ---")
    orb = get_mouse_on_keypress(
        "The RUN ENERGY ORB (foot icon near the minimap)")
    regions.run_orb_pos = (orb[0], orb[1])

    # ── Done ──
    print("\n" + "=" * 50)
    print("  CALIBRATION COMPLETE!")
    print("=" * 50)

    save_calibration(regions)
    print(f"\n  Saved to calibration.json")
    print("  Recalibrate only if you move/resize the client.\n")

    return regions
