"""
Bot state definitions.
"""

from enum import Enum, auto


class BotState(Enum):
    STARTING = auto()
    BANKING = auto()
    WALKING_TO_CONVEYOR = auto()
    DEPOSITING_ORE = auto()
    WALKING_TO_DISPENSER = auto()
    WAITING_FOR_BARS = auto()
    COLLECTING_BARS = auto()
    WALKING_TO_BANK = auto()
    STOPPED = auto()

    def __str__(self):
        labels = {
            BotState.STARTING: "Starting up",
            BotState.BANKING: "Banking",
            BotState.WALKING_TO_CONVEYOR: "Walking to conveyor",
            BotState.DEPOSITING_ORE: "Depositing ore",
            BotState.WALKING_TO_DISPENSER: "Walking to dispenser",
            BotState.WAITING_FOR_BARS: "Waiting for bars",
            BotState.COLLECTING_BARS: "Collecting bars",
            BotState.WALKING_TO_BANK: "Walking to bank",
            BotState.STOPPED: "Stopped",
        }
        return labels.get(self, self.name)
