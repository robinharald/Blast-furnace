"""
Tiered error recovery strategies.

Level 1: Retry (click didn't register)
Level 2: Reorient (rotate camera, re-scan)
Level 3: Relocate (teleport to bank, restart)
Level 4: Abandon (get new contract)
Level 5: Stop (too many errors)
"""
import logging
from typing import Optional

from bot.states import BotState

logger = logging.getLogger(__name__)

MAX_RETRIES_PER_STATE = 3
MAX_REORIENT_ATTEMPTS = 5
MAX_TOTAL_ERRORS = 10


class ErrorRecovery:
    """Manage error counting and recovery strategy selection."""

    def __init__(self):
        self._state_error_counts = {}
        self._total_errors = 0
        self._consecutive_errors = 0

    def record_error(self, state: BotState, error_type: str = "unknown") -> None:
        """Record an error in the given state."""
        key = state.name
        self._state_error_counts[key] = self._state_error_counts.get(key, 0) + 1
        self._total_errors += 1
        self._consecutive_errors += 1
        logger.warning(f"Error in {key}: {error_type} "
                       f"(state={self._state_error_counts[key]}, "
                       f"total={self._total_errors}, "
                       f"consecutive={self._consecutive_errors})")

    def record_success(self) -> None:
        """Reset consecutive error counter on success."""
        self._consecutive_errors = 0

    def get_recovery_action(self, state: BotState) -> str:
        """
        Determine the appropriate recovery action based on error counts.

        Returns:
            "retry" — try the same action again
            "reorient" — rotate camera, re-scan
            "relocate" — teleport to bank, restart contract
            "abandon" — abandon contract, get new one
            "stop" — stop the bot
        """
        state_errors = self._state_error_counts.get(state.name, 0)

        if self._consecutive_errors >= MAX_TOTAL_ERRORS:
            return "stop"

        if state_errors >= MAX_REORIENT_ATTEMPTS:
            return "abandon"

        if state_errors >= MAX_RETRIES_PER_STATE:
            return "reorient"

        return "retry"

    def reset_state_errors(self, state: BotState) -> None:
        """Reset error count for a specific state."""
        self._state_error_counts[state.name] = 0

    def should_stop(self) -> bool:
        """Check if the bot should stop due to too many errors."""
        return self._consecutive_errors >= MAX_TOTAL_ERRORS

    @property
    def total_errors(self) -> int:
        return self._total_errors
