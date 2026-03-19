#!/usr/bin/env python3
"""
OSRS Blast Furnace Bot - Entry Point

A standalone, injection-free bot that operates purely through
screen reading and OS-level mouse/keyboard input.

No bot client required. No game client modification.
Undetectable by client-side anti-cheat.

Usage:
    python main.py              # Normal start (settings + calibration if needed)
    python main.py --calibrate  # Force recalibration
    python main.py --help       # Show help
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ScreenRegions, load_calibration
from ui.setup_wizard import run_calibration, get_bot_settings
from bot.state_machine import BlastFurnaceStateMachine


BANNER = """
    ╔══════════════════════════════════════════════╗
    ║       OSRS BLAST FURNACE BOT  v1.0           ║
    ║                                              ║
    ║  Standalone · No injection · Color-based      ║
    ║  Supports all 8 bar types                    ║
    ╚══════════════════════════════════════════════╝
"""


def main():
    print(BANNER)

    # Parse args
    force_calibrate = "--calibrate" in sys.argv or "-c" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print("  Usage:")
        print("    python main.py              Start the bot")
        print("    python main.py --calibrate  Force screen recalibration")
        print("    python main.py --help       Show this help")
        print()
        print("  Prerequisites:")
        print("    1. OSRS client open and logged in")
        print("    2. Standing at the Blast Furnace in Keldagrim")
        print("    3. Gold deposited in the coffer")
        print("    4. Ores and coal in your bank")
        print("    5. Coal bag in inventory (if using)")
        print("    6. Ice gloves / Goldsmith gauntlets in bank or equipped")
        print("    7. Stamina potions in bank (if using)")
        print()
        print("  Supported bars:")
        from data.bars import BarType
        for bt in BarType:
            coal = f" + {bt.data.coal_per_bar} coal" if bt.data.requires_coal else ""
            print(f"    - {bt.data.name}: {bt.data.ore.primary_ore}{coal} (Lvl {bt.data.smithing_level})")
        print()
        return

    # ── Step 1: Screen calibration ──
    regions = ScreenRegions()

    if force_calibrate or not load_calibration(regions):
        print("  No calibration found (or --calibrate used).")
        print("  Starting screen calibration wizard...\n")
        regions = run_calibration(regions)
    else:
        print("  Loaded calibration from calibration.json")
        recal = input("  Recalibrate? (y/N): ").strip().lower()
        if recal == "y":
            regions = run_calibration(regions)

    # ── Step 2: Bot settings ──
    settings = get_bot_settings()

    # ── Step 3: Pre-flight checks ──
    print("\n" + "=" * 50)
    print("  PRE-FLIGHT CHECKLIST")
    print("=" * 50)
    print()
    print("  Please verify before starting:")
    print("  [1] OSRS client is open and visible")
    print("  [2] You are at the Blast Furnace")
    print("  [3] Coffer has gold deposited")
    print("  [4] Required ores are in your bank")
    if settings.use_coal_bag:
        print(f"  [5] Coal bag is in inventory slot {settings.coal_bag_slot}")
    if settings.use_stamina:
        print("  [6] Stamina potions are in your bank")
    print(f"\n  Press {settings.stop_key.upper()} at any time to stop the bot.")
    print()

    confirm = input("  Ready to start? (y/N): ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return

    # ── Step 4: Run the bot ──
    print("\n  Starting in 3 seconds... Switch to OSRS window!")
    import time
    time.sleep(3)

    machine = BlastFurnaceStateMachine(regions, settings)
    machine.run()

    print("\n  Bot stopped. Thanks for using Blast Furnace Bot!")


if __name__ == "__main__":
    main()
