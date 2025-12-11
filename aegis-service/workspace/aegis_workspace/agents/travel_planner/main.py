import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

from agents.main_agent import MainAgent
from config import Config
from utils.logger import setup_logging

# Load environment variables
load_dotenv()

def main():
    """Main entry point for the travel_planner agent."""
    parser = argparse.ArgumentParser(description="Travel Planner Agent")
    parser.add_argument(
        "--task", type=str, required=True, help="The travel planning task to execute."
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging."
    )

    args = parser.parse_args()

    # Initialize configuration
    config = Config()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Travel Planner Agent...")

    try:
        # Initialize and run the main agent
        main_agent = MainAgent(config=config)
        asyncio.run(main_agent.run(args.task))

        logger.info("Travel Planner Agent completed successfully.")

    except Exception as e:
        logger.exception(f"An error occurred during execution: {e}")


if __name__ == "__main__":
    main()