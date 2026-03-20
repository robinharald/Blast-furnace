#!/usr/bin/env python3
"""
OSRS Blast Furnace Bot - Entry Point

Launches the GUI. All settings, calibration, and bot control
happen through the tkinter interface.

Usage:
    python main.py              # Launch GUI
    python main.py --help       # Show help
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print()
        print("  OSRS Blast Furnace Bot")
        print("  Standalone, injection-free, color-based")
        print()
        print("  Usage:")
        print("    python main.py       Launch the GUI")
        print("    python main.py -h    Show this help")
        print()
        print("  Prerequisites:")
        print("    1. OSRS client open and logged in")
        print("    2. Standing at the Blast Furnace (mass world)")
        print("    3. Gold deposited in the coffer")
        print("    4. Ores in bank")
        print("    5. RuneLite Object Markers tagging:")
        print("       Bank chest     -> Blue     (FF0000FF)")
        print("       Conveyor belt  -> Magenta  (FFFF00FF)")
        print("       Bar dispenser  -> Lime     (FF00FF00)")
        print()
        from data.bars import BarType
        print("  Supported bars:")
        for bt in BarType:
            coal = f" + {bt.data.coal_per_bar} coal" if bt.data.requires_coal else ""
            print(f"    - {bt.data.name}: {bt.data.ore.primary_ore}{coal}"
                  f" (Lvl {bt.data.smithing_level})")
        print()
        return

    from ui.gui import BlastFurnaceGUI
    app = BlastFurnaceGUI()
    app.run()


if __name__ == "__main__":
    main()
