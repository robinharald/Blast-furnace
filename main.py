"""
Mahogany Homes Bot — Entry Point.

Launch the GUI application. Configures logging with:
- Console output (INFO level)
- Session log file (DEBUG level) — overwritten each session
- Error-only log file (WARNING+) — overwritten each session
- No log accumulation: each session starts clean
"""
import sys
import os
import logging

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# Fixed log file paths — overwritten each session
SESSION_LOG = os.path.join(LOG_DIR, "session.log")
ERROR_LOG = os.path.join(LOG_DIR, "errors.log")


def _setup_logging() -> None:
    """
    Configure multi-handler logging.

    All log files are OVERWRITTEN on each new session.
    No data accumulates between sessions.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt_detailed = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)-7s] %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fmt_console = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console: INFO level, short format
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt_console)
    root.addHandler(console)

    # Session log: DEBUG level, overwrite each session
    session_handler = logging.FileHandler(SESSION_LOG, mode="w", encoding="utf-8")
    session_handler.setLevel(logging.DEBUG)
    session_handler.setFormatter(fmt_detailed)
    root.addHandler(session_handler)

    # Error log: WARNING+ only, overwrite each session
    error_handler = logging.FileHandler(ERROR_LOG, mode="w", encoding="utf-8")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(fmt_detailed)
    root.addHandler(error_handler)

    logging.getLogger(__name__).info(
        f"Logging configured: session={SESSION_LOG}, errors={ERROR_LOG}"
    )


logger = logging.getLogger(__name__)


def main():
    _setup_logging()
    logger.info("Mahogany Homes Bot starting...")

    from ui.gui import MahoganyHomesGUI
    app = MahoganyHomesGUI()
    app.run()


if __name__ == "__main__":
    main()
