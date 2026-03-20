# OSRS Blast Furnace Bot

A standalone, injection-free Blast Furnace bot for Old School RuneScape. No bot client needed — operates purely through screen reading and OS-level mouse/keyboard input.

## How It Works

This bot does **not** modify or inject into the game client. It:

1. **Reads pixels** on your screen to understand game state (bank open, inventory contents, bar dispenser status)
2. **Moves the mouse** using the WindMouse algorithm — a mathematically human-like curve with wind deviation, gravity pull, and variable speed
3. **Clicks** with gaussian-distributed positional variance (never clicks the exact same pixel twice)
4. **Times actions** with fatigue simulation — gradually slows down over the session, takes micro-breaks, varies all delays

Nothing to detect on the client side. No signatures. No known bot client.

## Supported Bar Types

| Bar | Primary Ore | Coal (BF halved) | Smithing Lvl | XP/Bar |
|-----|-------------|-------------------|------------|--------|
| Bronze | Copper + Tin | 0 | 1 | 6.2 |
| Iron | Iron ore | 0 | 15 | 12.5 |
| Silver | Silver ore | 0 | 20 | 13.7 |
| Steel | Iron ore | 1 | 30 | 17.5 |
| Gold | Gold ore | 0 | 40 | 22.5 / 56.2* |
| Mithril | Mithril ore | 2 | 50 | 30.0 |
| Adamantite | Adamantite ore | 3 | 70 | 37.5 |
| Runite | Runite ore | 4 | 85 | 50.0 |

*56.2 XP with Goldsmith Gauntlets

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

Requirements: `pyautogui`, `Pillow`, `mss`, `numpy`, `keyboard`

### RuneLite Object Markers

Tag these 3 objects in RuneLite's Object Markers plugin with these ARGB colors:

| Object | Color | ARGB Hex |
|--------|-------|----------|
| Bank chest | Blue | `FF0000FF` |
| Conveyor belt | Magenta | `FFFF00FF` |
| Bar dispenser | Lime green | `FF00FF00` |

The bot finds objects by these colors — no minimap or position calibration needed.

### Before Starting

1. OSRS client open and logged in
2. Standing at the Blast Furnace in Keldagrim (mass world)
3. **Gold deposited in the coffer** (72,000 GP/hr for dwarven workers)
4. Ores and coal in your bank
5. Coal bag in your inventory (if using — it stays in a locked slot)
6. Ice gloves / Goldsmith gauntlets in bank or equipped
7. Stamina potions in bank (optional)
8. **Object Markers** set up (see above)

### Run

```bash
python main.py
```

The GUI opens. On first run, click **Calibrate** — only 7 mouse positions needed:
1. Game viewport (2 corners)
2. Inventory (2 slots)
3. Bank deposit button
4. Bank grid first slot
5. Run orb

Then select your bar type, toggle options, and hit **Start**.
Press **F6** (or your chosen key) at any time to stop.

## Architecture

```
blast_furnace/
├── main.py                     # Entry point
├── config.py                   # Screen regions, colors, settings
├── requirements.txt
├── bot/
│   ├── state_machine.py        # Core state machine with validation
│   ├── states.py               # State enum
│   └── session.py              # Statistics tracking
├── input/
│   └── mouse.py                # WindMouse human-like movement
├── screen/
│   └── capture.py              # Screenshot + pixel/color detection
├── game/
│   ├── inventory.py            # Inventory slot reading
│   ├── coal_bag.py             # Coal bag with locked slot
│   ├── bank.py                 # Bank open/deposit/withdraw/search
│   ├── object_finder.py        # RuneLite color marker detection
│   └── furnace.py              # Conveyor, dispenser, glove swapping
├── data/
│   └── bars.py                 # All bar types and ore definitions
├── anti_detect/
│   └── humanizer.py            # Fatigue, timing, micro-breaks
└── ui/
    ├── gui.py                  # Tkinter GUI (settings, log, controls)
    └── setup_wizard.py         # Minimal screen calibration (7 clicks)
```

## State Machine

```
BANKING → WALKING_TO_CONVEYOR → DEPOSITING_ORE
                                        │
                              ┌─────────┴──────────┐
                              │                    │
                         (coal-only trip)     (ore trip)
                              │                    │
                        WALKING_TO_BANK    WALKING_TO_DISPENSER
                              │                    │
                           BANKING         WAITING_FOR_BARS
                                                   │
                                           COLLECTING_BARS
                                                   │
                                           WALKING_TO_BANK
                                                   │
                                               BANKING
```

Every state:
- **Validates preconditions** before acting
- **Retries up to 3 times** on failure
- **Verifies results** after each action
- **Falls back to BANKING** on unrecoverable errors
- **Stops after 10 consecutive errors** (safety net)

Key mechanical invariants enforced:
- Coal is ALWAYS deposited before ore (prevents wrong bars like iron instead of steel)
- The bar dispenser is NOT clicked until bars are ready (untargetable before smelting completes)
- SPACE is pressed to confirm bar collection from the dispenser interface
- Ice gloves are equipped BEFORE clicking the dispenser (bars are hot)
- Goldsmith gauntlets are equipped BEFORE depositing gold ore (XP is awarded on deposit)
- Coal bag is emptied at the conveyor, not directly into the furnace
- Run energy is checked and toggled on every bank trip

## Coal Trip Cycling

For bars requiring coal, the bot alternates between coal and ore trips:

| Bar | Coal/Bar | Trip Pattern (with coal bag) |
|-----|----------|------------------------------|
| Steel | 1 | Every trip: 27 ore (inv) + 27 coal (bag) — always ore trip |
| Mithril | 2 | 1 coal trip → 1 ore trip (coal bag filled both) |
| Adamantite | 3 | 2 coal trips → 1 ore trip (coal bag filled all three) |
| Runite | 4 | 3 coal trips → 1 ore trip (coal bag filled all four) |

The coal bag is filled every trip. Steel is a special case: since it only
needs 1 coal per bar, the coal bag alone provides enough coal, so every
trip carries ore in the inventory. Excess coal stays in the furnace (max 254).

## Anti-Detection Features

### WindMouse Movement
- No straight-line paths — uses wind force + gravity physics
- Variable speed: fast in the middle, slow at start/end
- Distance-adaptive parameters (gentle for short moves, aggressive for long)
- Positional jitter on every click (gaussian distribution)

### Session Humanization
- **Fatigue simulation**: reactions slow by ~5% per hour (logarithmic)
- **Per-session personality**: randomized base speed, patience, precision
- **Micro-breaks**: 1-5 second pauses at random intervals
- **Long breaks**: 30-120 second AFK every 15-30 minutes
- **Mouse drift**: occasional idle mouse movements to neutral areas
- **Pre/post click delays**: simulates finger press and release timing

### No Signatures
- No game client modification or injection
- No known bot client frameworks
- No detectable driver hooks
- Pure screen pixel reading + standard OS input APIs
