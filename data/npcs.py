"""
All 12 Mahogany Homes contract NPCs with their locations, object IDs,
walk hints from teleport landing, and multi-floor flags.

World coordinates are from the RuneLite plugin source (Home.java).
Area bounding boxes define "inside the house" detection zones.
"""
from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class HouseArea:
    """Bounding box of a house in world coordinates."""
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class HouseNPC:
    """A Mahogany Homes contract NPC and their house."""
    name: str
    city: str                     # "varrock", "falador", "ardougne", "hosidius"
    world_x: int                  # NPC world coordinate X
    world_y: int                  # NPC world coordinate Y
    area: HouseArea               # House bounding box
    object_ids: Tuple[int, ...]   # Hotspot object IDs (reference only — bot detects by color)
    has_upstairs: bool = False    # Norman, Jess have second floors
    npc_upstairs: bool = False    # Is the NPC located upstairs?
    walk_bearing: str = "north"   # Compass direction from teleport landing
    walk_distance: str = "medium" # "short", "medium", "long"


# -----------------------------------------------------------------------
# Varrock NPCs
# -----------------------------------------------------------------------

BOB = HouseNPC(
    name="Bob", city="varrock",
    world_x=3238, world_y=3486,
    area=HouseArea(3234, 3482, 10, 10),
    object_ids=(39981, 39982, 39983, 39984, 39985, 39986, 39987, 39988),
    walk_bearing="north", walk_distance="long",
)

JEFF = HouseNPC(
    name="Jeff", city="varrock",
    world_x=3239, world_y=3450,
    area=HouseArea(3235, 3445, 10, 12),
    object_ids=(39989, 39990, 39991, 39992, 39993, 39994, 39995, 39996),
    walk_bearing="north-east", walk_distance="short",
)

SARAH = HouseNPC(
    name="Sarah", city="varrock",
    world_x=3235, world_y=3384,
    area=HouseArea(3232, 3381, 8, 7),
    object_ids=(39997, 39998, 39999, 40000, 40001, 40286),
    walk_bearing="south", walk_distance="medium",
)

# -----------------------------------------------------------------------
# Falador NPCs
# -----------------------------------------------------------------------

LARRY = HouseNPC(
    name="Larry", city="falador",
    world_x=3038, world_y=3364,
    area=HouseArea(3033, 3360, 10, 9),
    object_ids=(40095, 40096, 40097, 40098, 40099, 40297, 40298),
    walk_bearing="north-east", walk_distance="medium",
)

NORMAN = HouseNPC(
    name="Norman", city="falador",
    world_x=3038, world_y=3344,
    area=HouseArea(3034, 3341, 8, 8),
    object_ids=(40089, 40090, 40091, 40092, 40093, 40094, 40296),
    has_upstairs=True, npc_upstairs=True,
    walk_bearing="east", walk_distance="short",
)

TAU = HouseNPC(
    name="Tau", city="falador",
    world_x=3047, world_y=3345,
    area=HouseArea(3043, 3340, 10, 11),
    object_ids=(40083, 40084, 40085, 40086, 40087, 40088, 40295),
    walk_bearing="east", walk_distance="medium",
)

# -----------------------------------------------------------------------
# East Ardougne NPCs
# -----------------------------------------------------------------------

JESS = HouseNPC(
    name="Jess", city="ardougne",
    world_x=2621, world_y=3292,
    area=HouseArea(2611, 3290, 14, 7),
    object_ids=(40171, 40172, 40173, 40174, 40175, 40176, 40177, 40299),
    has_upstairs=True, npc_upstairs=True,
    walk_bearing="south-west", walk_distance="medium",
)

NOELLA = HouseNPC(
    name="Noella", city="ardougne",
    world_x=2659, world_y=3322,
    area=HouseArea(2652, 3317, 15, 8),
    object_ids=(40156, 40157, 40158, 40159, 40160, 40161, 40162, 40163),
    walk_bearing="north-east", walk_distance="short",
)

ROSS = HouseNPC(
    name="Ross", city="ardougne",
    world_x=2613, world_y=3316,
    area=HouseArea(2609, 3313, 11, 9),
    object_ids=(40164, 40165, 40166, 40167, 40168, 40169, 40170),
    walk_bearing="south-west", walk_distance="long",
)

# -----------------------------------------------------------------------
# Hosidius NPCs
# -----------------------------------------------------------------------

BARBARA = HouseNPC(
    name="Barbara", city="hosidius",
    world_x=1750, world_y=3534,
    area=HouseArea(1746, 3531, 10, 11),
    object_ids=(40011, 40012, 40013, 40014, 40015, 40293, 40294),
    walk_bearing="south", walk_distance="medium",
)

LEELA = HouseNPC(
    name="Leela", city="hosidius",
    world_x=1785, world_y=3592,
    area=HouseArea(1781, 3589, 9, 8),
    object_ids=(40007, 40008, 40009, 40010, 40290, 40291, 40292),
    walk_bearing="east", walk_distance="medium",
)

MARIAH = HouseNPC(
    name="Mariah", city="hosidius",
    world_x=1766, world_y=3621,
    area=HouseArea(1762, 3618, 10, 7),
    object_ids=(40002, 40003, 40004, 40005, 40006, 40287, 40288, 40289),
    walk_bearing="north-east", walk_distance="long",
)

# -----------------------------------------------------------------------
# Lookup helpers
# -----------------------------------------------------------------------

ALL_NPCS = {
    "bob": BOB, "jeff": JEFF, "sarah": SARAH,
    "larry": LARRY, "norman": NORMAN, "tau": TAU,
    "jess": JESS, "noella": NOELLA, "ross": ROSS,
    "barbara": BARBARA, "leela": LEELA, "mariah": MARIAH,
}

NPC_NAMES = list(ALL_NPCS.keys())

CITY_NPCS = {
    "varrock": [BOB, JEFF, SARAH],
    "falador": [LARRY, NORMAN, TAU],
    "ardougne": [JESS, NOELLA, ROSS],
    "hosidius": [BARBARA, LEELA, MARIAH],
}


def get_npc(name: str) -> HouseNPC:
    """Look up an NPC by name (case-insensitive)."""
    return ALL_NPCS[name.lower()]
