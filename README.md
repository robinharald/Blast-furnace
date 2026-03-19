# OSRS Blast Furnace Bot

A robust, plug-and-play bot for the Old School RuneScape Blast Furnace minigame. Built on DreamBot with a clean state-machine architecture.

## Supported Bar Types

| Bar | Primary Ore | Coal (at BF) | Smithing Lvl |
|-----|-------------|--------------|--------------|
| Bronze | Copper + Tin | 0 | 1 |
| Iron | Iron ore | 0 | 15 |
| Silver | Silver ore | 0 | 20 |
| Steel | Iron ore | 1 | 30 |
| Gold | Gold ore | 0 | 40 |
| Mithril | Mithril ore | 2 | 50 |
| Adamantite | Adamantite ore | 3 | 70 |
| Runite | Runite ore | 4 | 85 |

## Features

- **All bar types** supported with intelligent trip cycling
- **Coal bag** kept in a locked inventory slot (never deposited)
- **Goldsmith gauntlets** auto-equipped for gold ore, swapped to ice gloves for collection
- **Stamina potion** management with auto-drinking and 1-dose withdrawal
- **Anti-pattern** behaviors: random camera moves, tab checks, idle pauses
- **Live paint overlay** showing bars/hr, XP/hr, trips, runtime
- **Configuration GUI** to select bar type and toggle all options before starting
- **State machine** architecture for reliability and easy debugging

## Prerequisites

1. **Quest**: Started "The Giant Dwarf" (for Keldagrim access)
2. **Location**: Standing at the Blast Furnace in Keldagrim on a BF world (352, 355, 358, 386, 387)
3. **Coffer**: Gold coins deposited in the coffer before starting (72,000 GP/hr)
4. **Bank contents**:
   - Ores for your selected bar type
   - Coal (if smelting steel/mithril/adamantite/runite)
   - Stamina potions (1-dose recommended)
   - Ice gloves and/or Goldsmith gauntlets
5. **Inventory**: Coal bag (will be locked in slot 0 by default)
6. **Equipment**: Graceful outfit recommended for weight reduction

## Setup

### Build

```bash
mvn clean package
```

### Install

Copy the compiled JAR from `target/blast-furnace-bot-1.0.0.jar` into your DreamBot scripts folder:
- **Windows**: `C:\Users\<you>\DreamBot\Scripts\`
- **macOS**: `~/DreamBot/Scripts/`
- **Linux**: `~/DreamBot/Scripts/`

### Run

1. Launch DreamBot and log into OSRS
2. Travel to the Blast Furnace in Keldagrim
3. Deposit coins in the coffer
4. Ensure coal bag is in your inventory
5. Start the "Blast Furnace Bot" script from DreamBot's script panel
6. Select your bar type and options in the configuration GUI
7. Click "Start"

## Architecture

```
com.blastfurnace/
├── BlastFurnaceBot.java      # Main script entry point & state machine
├── core/
│   ├── BarType.java           # Enum of all bar types with ore/coal/XP data
│   ├── BotConfig.java         # Session configuration & item/object IDs
│   └── BotState.java          # State machine states
├── handlers/
│   ├── BankingHandler.java    # Banking, withdrawals, trip cycling
│   ├── CoalBagHandler.java    # Coal bag fill/empty, locked slot protection
│   └── FurnaceHandler.java    # Conveyor belt, bar dispenser, glove swapping
├── ui/
│   ├── ConfigGUI.java         # Pre-start configuration window
│   ├── PaintOverlay.java      # On-screen stats rendering
│   └── StatsTracker.java      # Session statistics tracking
└── utils/
    ├── AntiPattern.java       # Human-like behavior simulation
    └── SleepUtils.java        # Randomized delay utilities
```

## Trip Cycle Logic

For bars requiring coal, the bot uses an intelligent trip cycle:

- **Steel (1 coal/bar)**: Fill coal bag → deposit coal + ore each trip
- **Mithril (2 coal/bar)**: 1 coal trip (bag + inventory) → 1 ore trip (bag coal + ore)
- **Adamantite (3 coal/bar)**: 2 coal trips → 1 ore trip
- **Runite (4 coal/bar)**: 3 coal trips → 1 ore trip

The coal bag is filled every trip regardless, maximizing coal throughput.

## Notes

- The bot auto-stops when supplies run out
- Session summary is logged on exit
- Smithing level 60+ avoids the 2,500 GP/10 min Foreman fee
- For best XP rates, use Gold with Goldsmith Gauntlets (~370-400K XP/hr)
- For best profit, use Runite bars (~1-3M GP/hr depending on GE prices)
