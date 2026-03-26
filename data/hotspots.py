"""
Hotspot varbit mappings and object ID groupings.

These are REFERENCE DATA — the bot detects hotspots by RuneLite overlay color,
not by reading varbits or object IDs from memory. This data is documented
for completeness and to help verify RuneLite plugin configuration.

Varbits are read by the RuneLite Mahogany Homes plugin internally.
The plugin uses them to decide which objects to highlight.

Varbit values:
  0 = default (no action needed)
  1 = needs repair
  2 = repaired (done)
  3 = needs removal
  4 = needs building
  5-8 = built (tier 1-4, done)
"""

# Varbit IDs for the 8 possible hotspots per house
HOTSPOT_VARBITS = {
    1: 10554,
    2: 10555,
    3: 10556,
    4: 10557,
    5: 10558,
    6: 10559,
    7: 10560,
    8: 10561,
}

# Object IDs grouped by hotspot varbit index
# Each varbit can correspond to objects across multiple NPCs' houses
HOTSPOT_OBJECTS_BY_VARBIT = {
    10554: (39981, 39989, 39997, 40002, 40007, 40011, 40083, 40156, 40164, 40171, 40296, 40297),
    10555: (39982, 39990, 39998, 40008, 40084, 40089, 40095, 40157, 40165, 40172, 40287, 40293),
    10556: (39983, 39991, 39999, 40003, 40012, 40085, 40090, 40096, 40158, 40166, 40173, 40290),
    10557: (39984, 39992, 40000, 40086, 40091, 40097, 40159, 40167, 40174, 40288, 40291, 40294),
    10558: (39985, 39993, 40004, 40009, 40013, 40087, 40092, 40160, 40168, 40175, 40286, 40298),
    10559: (39986, 39994, 40001, 40005, 40010, 40014, 40088, 40093, 40098, 40161, 40169, 40176),
    10560: (39987, 39995, 40006, 40015, 40094, 40099, 40162, 40170, 40177, 40292, 40295),
    10561: (39988, 39996, 40163, 40289, 40299),
}

# Hotspot action types (from HotspotObjects.java)
# B1-B4 = build requiring 1-4 planks
# RP = repair requiring 1 plank
# SB = repair requiring 1 steel bar
HOTSPOT_TYPES = {
    "B1": {"material": "plank", "quantity": 1},
    "B2": {"material": "plank", "quantity": 2},
    "B3": {"material": "plank", "quantity": 3},
    "B4": {"material": "plank", "quantity": 4},
    "RP": {"material": "plank", "quantity": 1},
    "SB": {"material": "steel_bar", "quantity": 1},
}

# Staircase/ladder object IDs found in multi-floor houses (Norman, Jess)
STAIRCASE_OBJECT_IDS = (
    17026, 16685, 16683, 16679,
    24075, 24076, 24082, 24085,
    11794, 11802, 11797, 11799,
    11789, 11793,
)
