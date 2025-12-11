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
    parser = argparse.ArgumentParser(description="Hugging Face Web Scraping Agent")
    parser.add_argument("--output_format", type=str, default="json", choices=["json", "csv", "txt"], help="Output format for scraped data")
    parser.add_argument("--log_level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level")
    parser.add_argument("--max_pages", type=int, default=5, help="Maximum number of pages to scrape")
    args = parser.parse_args()

    # Configure logging
    setup_logging(log_level=args.log_level)
    logger = logging.getLogger(__name__)

    # Load configuration
    config = Config()
    config.output_format = args.output_format
    config.max_pages = args.max_pages

    try:
        # Initialize and run the agent
        agent = MainAgent(config=config)
        asyncio.run(agent.run())

    except Exception as e:
        logger.exception("An unexpected error occurred during agent execution:")

if __name__ == "__main__":
    main()