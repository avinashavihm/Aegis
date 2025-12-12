import argparse
import os
import logging
from dotenv import load_dotenv
from agents.main_agent import MainAgent
from utils.logger import setup_logging
from config import Config

# Load environment variables
load_dotenv()

def main():
    """
    Main entry point for the travel agent application.
    """
    parser = argparse.ArgumentParser(description="Travel Agent Application")
    parser.add_argument(
        "--task", type=str, required=True, help="The main task for the travel agent."
    )
    args = parser.parse_args()

    # Initialize configuration
    config = Config()

    # Setup logging
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Travel Agent Application...")

    # Initialize the main agent
    main_agent = MainAgent(config=config)

    try:
        # Execute the main task
        result = main_agent.execute_task(args.task)
        print(f"Final Result (first 500 chars): {result[:500]}...")
        if len(result) > 500:
            print(f"... (truncated, total length: {len(result)})")
        logger.info("Travel Agent Application finished successfully.")

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()