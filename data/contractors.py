"""
Mahogany Homes contractor NPCs — where you get contracts (Mode B).

Each city has one contractor. After completing a contract, walk to the
contractor in the SAME city to get the next one.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Contractor:
    name: str
    city: str
    description: str              # Human-readable location hint
    walk_bearing: str             # Direction from typical teleport landing
    walk_distance: str            # "short", "medium"


AMY = Contractor(
    name="Amy", city="falador",
    description="South of Falador Park, next to Estate Agent",
    walk_bearing="south", walk_distance="short",
)

MARLO = Contractor(
    name="Marlo", city="varrock",
    description="North of Varrock square",
    walk_bearing="north", walk_distance="short",
)

ELLIE = Contractor(
    name="Ellie", city="ardougne",
    description="West of East Ardougne teleport spot",
    walk_bearing="west", walk_distance="short",
)

ANGELO = Contractor(
    name="Angelo", city="hosidius",
    description="Northeast of Hosidius, near Xeric's Glade",
    walk_bearing="north-east", walk_distance="medium",
)

ALL_CONTRACTORS = {
    "falador": AMY,
    "varrock": MARLO,
    "ardougne": ELLIE,
    "hosidius": ANGELO,
}


def get_contractor(city: str) -> Contractor:
    """Get the contractor for a given city."""
    return ALL_CONTRACTORS[city.lower()]
