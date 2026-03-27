"""
Tiered error recovery strategies, backed by ErrorTracker.

Level 1: Retry (click didn't register)
Level 2: Reorient (rotate camera, re-scan)
Level 3: Relocate (teleport to bank, restart)
Level 4: Abandon (get new contract)
Level 5: Stop (too many errors)
"""
import logging
from typing import Optional

from bot.states import BotState
from bot.error_logger import ErrorTracker, ErrorType, GameContext

logger = logging.getLogger(__name__)

MAX_RETRIES_PER_STATE = 3
MAX_REORIENT_ATTEMPTS = 5
MAX_CONSECUTIVE_ERRORS = 10


class ErrorRecovery:
    """Manage error counting and recovery strategy selection."""

    def __init__(self, tracker: ErrorTracker):
        self.tracker = tracker
        self._consecutive_errors = 0

    def record_error(
        self,
        state: BotState,
        error_type: ErrorType,
        message: str,
        module: str = "",
        exception: Optional[Exception] = None,
        context: Optional[GameContext] = None,
    ) -> None:
        """Record an error with full context via the ErrorTracker."""
        event = self.tracker.record_error(
            error_type=error_type,
            state=state.name,
            message=message,
            module=module,
            exception=exception,
            context=context,
        )
        self._consecutive_errors += 1

    def record_state_attempt(self, state: BotState) -> None:
        """Record that a state handler was attempted."""
        self.tracker.record_state_attempt(state.name)

    def record_success(self) -> None:
        """Reset consecutive error counter on success."""
        self._consecutive_errors = 0

    def get_recovery_action(self, state: BotState) -> str:
        """
        Determine the appropriate recovery action based on error history.

        Returns:
            "retry" — try the same action again
            "reorient" — rotate camera, re-scan
            "relocate" — teleport to bank, restart contract
            "abandon" — abandon contract, get new one
            "stop" — stop the bot
        """
        # Check consecutive errors (across all states)
        if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            action = "stop"
        else:
            # Check consecutive errors in THIS specific state
            state_consecutive = self.tracker.consecutive_errors_in_state(state.name)

            if state_consecutive >= MAX_REORIENT_ATTEMPTS:
                action = "abandon"
            elif state_consecutive >= MAX_RETRIES_PER_STATE:
                action = "reorient"
            else:
                action = "retry"

        logger.info(f"Recovery action for {state.name}: {action} "
                     f"(consecutive={self._consecutive_errors}, "
                     f"state_consec={self.tracker.consecutive_errors_in_state(state.name)})")

        return action

    def record_recovery_outcome(self, action: str, success: bool) -> None:
        """Record whether a recovery attempt succeeded."""
        self.tracker.record_recovery_outcome(action, success)

        # Also update the most recent error event
        if self.tracker.history:
            self.tracker.update_event_recovery(
                self.tracker.history[-1], action, success
            )

    def should_stop(self) -> bool:
        """Check if the bot should stop due to too many errors."""
        return self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS

    @property
    def total_errors(self) -> int:
        return self.tracker.total_errors

    def reset(self) -> None:
        """Reset for a new session."""
        self._consecutive_errors = 0
        self.tracker.reset()
