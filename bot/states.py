"""
Bot state definitions.
"""

from enum import Enum, auto


class BotState(Enum):
    STARTING = auto()
    BANKING = auto()
    WALKING_TO_CONVEYOR = auto()
    DEPOSITING_ORE = auto()
    COLLECTING_PREVIOUS_BARS = auto()  # After depositing: collect bars from PREVIOUS trip
    WALKING_TO_DISPENSER = auto()      # First trip only: walk to dispenser to wait
    WAITING_FOR_BARS = auto()          # First trip only: wait for bars to smelt
    COLLECTING_BARS_FIRST_TRIP = auto() # First trip only: collect first batch
    WALKING_TO_BANK = auto()
    STOPPED = auto()

    def __str__(self):
        labels = {
            BotState.STARTING: "Starting up",
            BotState.BANKING: "Banking",
            BotState.WALKING_TO_CONVEYOR: "Walking to conveyor",
            BotState.DEPOSITING_ORE: "Depositing ore",
            BotState.COLLECTING_PREVIOUS_BARS: "Collecting previous bars",
            BotState.WALKING_TO_DISPENSER: "Walking to dispenser",
            BotState.WAITING_FOR_BARS: "Waiting for bars",
            BotState.COLLECTING_BARS_FIRST_TRIP: "Collecting bars (first trip)",
            BotState.WALKING_TO_BANK: "Walking to bank",
            BotState.STOPPED: "Stopped",
        }
        return labels.get(self, self.name)
