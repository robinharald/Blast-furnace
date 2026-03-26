"""
Mahogany Homes Bot — Entry Point.

Launch the GUI application.
"""
import sys
import os
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("mahogany_homes.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Mahogany Homes Bot starting...")

    from ui.gui import MahoganyHomesGUI
    app = MahoganyHomesGUI()
    app.run()


if __name__ == "__main__":
    main()
