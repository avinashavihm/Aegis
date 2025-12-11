import logging
import sys

def setup_logging(level=logging.INFO):
    """
    Sets up logging configuration.

    Args:
        level: The logging level (e.g., logging.INFO, logging.DEBUG).
    """
    logging.basicConfig(
        stream=sys.stdout,  # Output to console
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Optional: Configure logging to a file as well
    # handler = logging.FileHandler('travel_planner.log')
    # handler.setLevel(level)
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # handler.setFormatter(formatter)
    # logging.getLogger('').addHandler(handler)  # Attach to root logger