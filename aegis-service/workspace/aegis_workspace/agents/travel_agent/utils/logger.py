import logging
import sys

def setup_logging(log_level="INFO"):
    """
    Sets up the logging configuration for the application.

    Args:
        log_level (str): The desired log level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    root = logging.getLogger()
    root.setLevel(numeric_level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.info(f"Logging initialized with level: {log_level}")