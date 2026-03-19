"""
Setup wizard for calibrating screen positions.

Walks the user through clicking key positions on the game screen
so the bot knows where everything is. Saves to calibration.json.

This makes the bot truly plug-and-play — works on any resolution,
any client size, any monitor.
"""

import time
import json
import keyboard
import pyautogui
from config import ScreenRegions, BotSettings, save_calibration, load_calibration
from data.bars import BarType


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
    Guides the user through clicking every key position.
    """
    print("\n" + "=" * 50)
    print("  BLAST FURNACE BOT - SCREEN CALIBRATION")
    print("=" * 50)
    print("\n  This wizard will ask you to position your mouse")
    print("  on key game elements and press SPACE to capture.")
    print("  Make sure OSRS is visible and you're at the Blast Furnace.\n")
    print("  Press ENTER to begin...")
    input()

    # ── Game viewport ──
    print("\n--- GAME VIEWPORT ---")
    tl = get_mouse_on_keypress("Hover over the TOP-LEFT corner of the game viewport")
    br = get_mouse_on_keypress("Hover over the BOTTOM-RIGHT corner of the game viewport")
    regions.game_x = tl[0]
    regions.game_y = tl[1]
    regions.game_w = br[0] - tl[0]
    regions.game_h = br[1] - tl[1]

    # ── Inventory ──
    print("\n--- INVENTORY GRID ---")
    inv_tl = get_mouse_on_keypress("Hover over the CENTER of inventory SLOT 1 (top-left slot)")
    inv_br = get_mouse_on_keypress("Hover over the CENTER of inventory SLOT 28 (bottom-right slot)")
    regions.inv_x = inv_tl[0] - regions.inv_slot_w // 2
    regions.inv_y = inv_tl[1] - regions.inv_slot_h // 2
    # Calculate slot dimensions from the two corner slots
    regions.inv_slot_w = (inv_br[0] - inv_tl[0]) // (regions.inv_cols - 1)
    regions.inv_slot_h = (inv_br[1] - inv_tl[1]) // (regions.inv_rows - 1)
    # Adjust origin to true top-left of slot grid
    regions.inv_x = inv_tl[0] - regions.inv_slot_w // 2
    regions.inv_y = inv_tl[1] - regions.inv_slot_h // 2

    # ── Minimap ──
    print("\n--- MINIMAP ---")
    mm = get_mouse_on_keypress("Hover over the CENTER of the minimap (your player dot)")
    regions.minimap_cx = mm[0]
    regions.minimap_cy = mm[1]

    # ── Key game objects ──
    print("\n--- GAME OBJECTS ---")
    print("  Make sure you can see these objects on your screen.\n")

    regions.bank_pos = get_mouse_on_keypress(
        "Hover over the BANK CHEST (the chest you click to open the bank)")
    regions.conveyor_pos = get_mouse_on_keypress(
        "Hover over the CONVEYOR BELT (where you deposit ore)")
    regions.dispenser_pos = get_mouse_on_keypress(
        "Hover over the BAR DISPENSER (where you collect bars)")

    # ── Minimap navigation points ──
    print("\n--- MINIMAP NAVIGATION ---")
    print("  These are points on the MINIMAP (not game screen).")
    print("  The bot will click these to walk between locations.\n")

    regions.minimap_bank = get_mouse_on_keypress(
        "On the MINIMAP, hover over where the bank chest is shown")
    regions.minimap_conveyor = get_mouse_on_keypress(
        "On the MINIMAP, hover over where the conveyor belt is shown")
    regions.minimap_dispenser = get_mouse_on_keypress(
        "On the MINIMAP, hover over where the bar dispenser is shown")

    # ── Bank interface elements ──
    print("\n--- BANK INTERFACE ---")
    print("  Please OPEN YOUR BANK now, then capture these positions.\n")
    input("  Press ENTER when the bank is open...")

    regions.bank_deposit_inv_btn = get_mouse_on_keypress(
        "Hover over the 'Deposit inventory' button (backpack icon at bottom of bank)")
    regions.bank_close_btn = get_mouse_on_keypress(
        "Hover over the bank CLOSE button (X at top-right of bank)")

    # Bank search region
    search_tl = get_mouse_on_keypress(
        "Hover over the SEARCH ICON (magnifying glass at bottom of bank)")
    regions.bank_search_region = (search_tl[0] - 15, search_tl[1] - 15, 30, 30)

    # ── Bar dispenser collection widget ──
    print("\n--- BAR COLLECTION ---")
    print("  If you have bars ready to collect, click the dispenser to")
    print("  open the collection widget. If not, estimate the position.\n")

    regions.bar_collect_btn = get_mouse_on_keypress(
        "Hover over where you CLICK TO COLLECT BARS in the dispenser widget\n"
        "     (the bar icon in the collection interface)")

    # ── Done ──
    print("\n" + "=" * 50)
    print("  CALIBRATION COMPLETE!")
    print("=" * 50)

    # Save calibration
    save_calibration(regions)
    print(f"\n  Saved to calibration.json")
    print("  You won't need to recalibrate unless you move/resize the client.\n")

    return regions


def get_bot_settings():
    """
    Interactive settings selection.
    Returns configured BotSettings.
    """
    settings = BotSettings()

    print("\n" + "=" * 50)
    print("  BLAST FURNACE BOT - SETTINGS")
    print("=" * 50)

    # Bar type selection
    print("\n  Select bar type to smelt:\n")
    bar_types = list(BarType)
    for i, bt in enumerate(bar_types):
        coal_info = f" ({bt.data.coal_per_bar} coal)" if bt.data.requires_coal else ""
        print(f"    {i + 1}. {bt.data.name}{coal_info} - Lvl {bt.data.smithing_level}")

    while True:
        try:
            choice = int(input(f"\n  Enter choice (1-{len(bar_types)}): "))
            if 1 <= choice <= len(bar_types):
                settings.bar_type = bar_types[choice - 1]
                break
        except ValueError:
            pass
        print("  Invalid choice, try again.")

    print(f"\n  Selected: {settings.bar_type.data.name}")

    # Coal bag
    if settings.bar_type.data.requires_coal:
        use_cb = input("\n  Use coal bag? (Y/n): ").strip().lower()
        settings.use_coal_bag = use_cb != "n"
        if settings.use_coal_bag:
            while True:
                try:
                    slot = int(input("  Coal bag inventory slot (0-27, default 0): ").strip() or "0")
                    if 0 <= slot <= 27:
                        settings.coal_bag_slot = slot
                        break
                except ValueError:
                    pass
                print("  Invalid slot, try again.")
    else:
        settings.use_coal_bag = False

    # Stamina
    use_stam = input("\n  Use stamina potions? (Y/n): ").strip().lower()
    settings.use_stamina = use_stam != "n"

    # Gold-specific options
    if settings.bar_type == BarType.GOLD:
        use_gs = input("  Use goldsmith gauntlets? (Y/n): ").strip().lower()
        settings.use_goldsmith_gauntlets = use_gs != "n"

    # Ice gloves
    use_ice = input("  Use ice gloves? (Y/n): ").strip().lower()
    settings.use_ice_gloves = use_ice != "n"

    # Stop key
    stop = input(f"  Emergency stop key (default F6): ").strip().lower()
    if stop:
        settings.stop_key = stop

    print(f"\n  Configuration complete!")
    print(f"  Bar: {settings.bar_type.data.name}")
    print(f"  Coal bag: {'Slot ' + str(settings.coal_bag_slot) if settings.use_coal_bag else 'No'}")
    print(f"  Stamina: {'Yes' if settings.use_stamina else 'No'}")
    print(f"  Stop key: {settings.stop_key.upper()}")
    print()

    return settings
