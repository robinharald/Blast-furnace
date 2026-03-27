"""
Structured error logging and tracking system.

Every error in the bot is captured as an ErrorEvent with full context:
- What happened (type, message, exception)
- When it happened (timestamp)
- Where in the bot it happened (state, module)
- What the bot was doing (contract NPC, current action)
- What the game looked like (inventory counts, positions)

Error history is stored in memory and written to a dedicated error log file.
Supports querying/aggregating errors for pattern detection and debugging.
"""
import json
import os
import time
import traceback
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Optional, List, Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

ERROR_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
ERROR_LOG_FILE = os.path.join(ERROR_LOG_DIR, "errors.jsonl")
ERROR_REPORT_FILE = os.path.join(ERROR_LOG_DIR, "error_report.txt")


class ErrorType(Enum):
    """Categorized error types for aggregation and pattern detection."""
    # Detection failures
    HOTSPOT_NOT_FOUND = auto()
    DOOR_NOT_FOUND = auto()
    STAIRCASE_NOT_FOUND = auto()
    BANK_NOT_FOUND = auto()
    NPC_NOT_FOUND = auto()
    CONTRACTOR_NOT_FOUND = auto()

    # Interaction failures
    CLICK_NO_RESPONSE = auto()
    BUILD_TIMEOUT = auto()
    DIALOGUE_STUCK = auto()
    DIALOGUE_NOT_OPENED = auto()
    BANK_NOT_OPENED = auto()

    # Navigation failures
    TELEPORT_FAILED = auto()
    WALK_STUCK = auto()
    FLOOR_CHANGE_FAILED = auto()

    # Contract failures
    OCR_PARSE_FAILED = auto()
    CONTRACT_NPC_UNKNOWN = auto()
    NO_MATERIALS = auto()
    NO_RUNES = auto()

    # Spell failures
    NPC_CONTACT_FAILED = auto()
    SPELL_NOT_AVAILABLE = auto()

    # System failures
    SCREENSHOT_FAILED = auto()
    STATE_INVALID = auto()
    HANDLER_EXCEPTION = auto()
    RECOVERY_FAILED = auto()

    # General
    TIMEOUT = auto()
    UNKNOWN = auto()


@dataclass
class GameContext:
    """Snapshot of game state at the time of an error."""
    contract_npc: Optional[str] = None
    contract_city: Optional[str] = None
    contract_tier: Optional[str] = None
    hotspots_completed: int = 0
    plank_count: int = -1          # -1 = unknown
    steel_bar_count: int = -1
    current_floor: int = 0         # 0 = ground, 1 = upstairs
    run_energy_low: bool = False
    session_minutes: float = 0.0
    fatigue_factor: float = 1.0
    last_click_pos: Optional[tuple] = None


@dataclass
class ErrorEvent:
    """A single error occurrence with full context."""
    timestamp: float = field(default_factory=time.time)
    timestamp_str: str = ""
    error_type: str = "UNKNOWN"
    state: str = ""
    module: str = ""
    message: str = ""
    exception_type: Optional[str] = None
    exception_msg: Optional[str] = None
    traceback_str: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    recovery_action: Optional[str] = None
    recovery_success: Optional[bool] = None

    def __post_init__(self):
        if not self.timestamp_str:
            self.timestamp_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)
            )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_log_line(self) -> str:
        """Human-readable single-line summary."""
        parts = [
            f"[{self.timestamp_str}]",
            f"[{self.error_type}]",
            f"state={self.state}",
        ]
        if self.module:
            parts.append(f"module={self.module}")
        parts.append(self.message)
        if self.exception_type:
            parts.append(f"({self.exception_type}: {self.exception_msg})")
        if self.context:
            npc = self.context.get("contract_npc", "")
            if npc:
                parts.append(f"npc={npc}")
        return " | ".join(parts)


class ErrorTracker:
    """
    Central error tracking system.

    Records all errors with context, writes to JSONL file for post-session
    analysis, and provides aggregation queries for pattern detection.
    """

    def __init__(self, max_history: int = 500):
        self.max_history = max_history

        # Ensure log directory exists
        os.makedirs(ERROR_LOG_DIR, exist_ok=True)

        # Reset everything for this session (overwrite, not append)
        self.reset()

        # Open JSONL file in WRITE mode (overwrite previous session)
        self._file = None
        try:
            self._file = open(ERROR_LOG_FILE, "w")
        except OSError as e:
            logger.warning(f"Could not open error log file: {e}")

    def reset(self) -> None:
        """
        Clear all error history and counters.
        Called on every new session start — previous session data is wiped.
        """
        self.history: List[ErrorEvent] = []
        self._type_counts: Dict[str, int] = defaultdict(int)
        self._state_counts: Dict[str, int] = defaultdict(int)
        self._state_attempts: Dict[str, int] = defaultdict(int)
        self._recovery_outcomes: Dict[str, List[bool]] = defaultdict(list)

        # Overwrite the JSONL file if it's open
        if hasattr(self, '_file') and self._file and not self._file.closed:
            self._file.close()
            try:
                self._file = open(ERROR_LOG_FILE, "w")
            except OSError:
                pass

    def record_error(
        self,
        error_type: ErrorType,
        state: str,
        message: str,
        module: str = "",
        exception: Optional[Exception] = None,
        context: Optional[GameContext] = None,
    ) -> ErrorEvent:
        """
        Record a structured error event.

        Args:
            error_type: Categorized error type
            state: Current BotState name
            message: Human-readable description
            module: Which module raised the error
            exception: The exception object (if any)
            context: Game state snapshot
        """
        event = ErrorEvent(
            error_type=error_type.name,
            state=state,
            module=module,
            message=message,
        )

        if exception:
            event.exception_type = type(exception).__name__
            event.exception_msg = str(exception)
            event.traceback_str = traceback.format_exc()

        if context:
            event.context = asdict(context)

        # Store in memory
        self.history.append(event)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # Update counters
        self._type_counts[event.error_type] += 1
        self._state_counts[state] += 1

        # Write to file
        self._write_event(event)

        # Log it
        logger.error(event.to_log_line())

        return event

    def record_state_attempt(self, state: str) -> None:
        """Record that a state handler was attempted (for success rate calc)."""
        self._state_attempts[state] += 1

    def record_recovery_outcome(self, action: str, success: bool) -> None:
        """Record whether a recovery action succeeded."""
        self._recovery_outcomes[action].append(success)

    def update_event_recovery(self, event: ErrorEvent, action: str, success: bool) -> None:
        """Update an error event with its recovery outcome."""
        event.recovery_action = action
        event.recovery_success = success
        self.record_recovery_outcome(action, success)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def errors_in_last_minutes(self, minutes: float) -> List[ErrorEvent]:
        """Get all errors from the last N minutes."""
        cutoff = time.time() - (minutes * 60)
        return [e for e in self.history if e.timestamp >= cutoff]

    def errors_by_type(self, error_type: ErrorType) -> List[ErrorEvent]:
        """Get all errors of a specific type."""
        return [e for e in self.history if e.error_type == error_type.name]

    def errors_by_state(self, state: str) -> List[ErrorEvent]:
        """Get all errors in a specific state."""
        return [e for e in self.history if e.state == state]

    def recent_errors(self, count: int = 10) -> List[ErrorEvent]:
        """Get the N most recent errors."""
        return self.history[-count:]

    def consecutive_errors_in_state(self, state: str) -> int:
        """Count consecutive recent errors in a specific state (unbroken by success)."""
        count = 0
        for event in reversed(self.history):
            if event.state == state:
                count += 1
            else:
                break
        return count

    def state_success_rate(self, state: str) -> float:
        """Calculate the success rate for a state (1.0 = all succeeded)."""
        attempts = self._state_attempts.get(state, 0)
        errors = self._state_counts.get(state, 0)
        if attempts == 0:
            return 1.0
        return max(0.0, 1.0 - (errors / attempts))

    def recovery_success_rate(self, action: str) -> float:
        """Calculate how often a recovery action succeeds."""
        outcomes = self._recovery_outcomes.get(action, [])
        if not outcomes:
            return 0.0
        return sum(outcomes) / len(outcomes)

    # ------------------------------------------------------------------
    # Aggregation / Summary
    # ------------------------------------------------------------------

    def type_summary(self) -> Dict[str, int]:
        """Error counts by type."""
        return dict(sorted(self._type_counts.items(), key=lambda x: -x[1]))

    def state_summary(self) -> Dict[str, int]:
        """Error counts by state."""
        return dict(sorted(self._state_counts.items(), key=lambda x: -x[1]))

    def session_summary(self) -> str:
        """Human-readable session error summary."""
        total = len(self.history)
        if total == 0:
            return "No errors recorded"

        lines = [f"Total errors: {total}"]

        # Top error types
        lines.append("By type:")
        for etype, count in list(self.type_summary().items())[:5]:
            lines.append(f"  {etype}: {count}")

        # Top error states
        lines.append("By state:")
        for state, count in list(self.state_summary().items())[:5]:
            rate = self.state_success_rate(state)
            lines.append(f"  {state}: {count} errors ({rate:.0%} success rate)")

        # Recovery effectiveness
        if self._recovery_outcomes:
            lines.append("Recovery effectiveness:")
            for action, outcomes in self._recovery_outcomes.items():
                rate = sum(outcomes) / len(outcomes) if outcomes else 0
                lines.append(f"  {action}: {rate:.0%} ({len(outcomes)} attempts)")

        return "\n".join(lines)

    @property
    def total_errors(self) -> int:
        return len(self.history)

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def _write_event(self, event: ErrorEvent) -> None:
        """Write a single event to the JSONL error log."""
        if self._file:
            try:
                line = json.dumps(event.to_dict(), default=str)
                self._file.write(line + "\n")
                self._file.flush()
            except (OSError, TypeError) as e:
                logger.warning(f"Failed to write error event: {e}")

    def flush(self) -> None:
        """Flush the error log file."""
        if self._file:
            self._file.flush()

    def close(self) -> None:
        """Close the error log file."""
        if self._file:
            self._file.close()
            self._file = None

    def export_session_report(self, filepath: Optional[str] = None) -> str:
        """
        Export a full session error report to a text file (overwrites previous).
        Returns the file path.
        """
        if filepath is None:
            filepath = ERROR_REPORT_FILE

        with open(filepath, "w") as f:
            f.write("=" * 70 + "\n")
            f.write("MAHOGANY HOMES BOT — ERROR REPORT\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")

            f.write(self.session_summary() + "\n\n")

            f.write("-" * 70 + "\n")
            f.write("FULL ERROR HISTORY\n")
            f.write("-" * 70 + "\n\n")

            for event in self.history:
                f.write(event.to_log_line() + "\n")
                if event.traceback_str:
                    f.write(f"  Traceback:\n")
                    for line in event.traceback_str.strip().split("\n"):
                        f.write(f"    {line}\n")
                if event.context:
                    f.write(f"  Context: {json.dumps(event.context, default=str)}\n")
                if event.recovery_action:
                    outcome = "OK" if event.recovery_success else "FAILED"
                    f.write(f"  Recovery: {event.recovery_action} -> {outcome}\n")
                f.write("\n")

        logger.info(f"Error report exported to {filepath}")
        return filepath


def build_context(bot) -> GameContext:
    """
    Build a GameContext snapshot from the current bot state.
    Call this when an error occurs to capture what the bot was doing.
    """
    ctx = GameContext()

    try:
        if bot.contract and bot.contract.state.npc:
            ctx.contract_npc = bot.contract.state.npc.name
            ctx.contract_city = bot.contract.state.npc.city
            ctx.hotspots_completed = bot.contract.state.hotspots_completed
            ctx.current_floor = 1 if bot.contract.state.visited_upstairs else 0

        if bot.contract and bot.contract.state.tier:
            ctx.contract_tier = bot.contract.state.tier.name

        ctx.session_minutes = bot.humanizer._session_minutes()
        ctx.fatigue_factor = bot.humanizer.fatigue_factor()

        # Try to get inventory counts (may fail if not in correct tab)
        try:
            ctx.plank_count = bot.inventory.count_planks(
                bot.tier_data.plank_color, bot.tier_data.plank_tolerance
            )
            ctx.steel_bar_count = bot.inventory.count_steel_bars()
        except Exception:
            pass

        try:
            ctx.run_energy_low = bot.run_energy.is_energy_low()
        except Exception:
            pass

        if bot.worker and bot.worker._last_click_pos:
            ctx.last_click_pos = bot.worker._last_click_pos

    except Exception as e:
        logger.debug(f"Context capture partially failed: {e}")

    return ctx
