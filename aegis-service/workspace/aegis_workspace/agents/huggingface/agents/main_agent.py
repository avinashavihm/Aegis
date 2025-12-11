import asyncio
import logging
import json
import csv
import os

from typing import List, Dict

from aegis.types import Agent
from aegis.tools import read_file, write_file, execute_python
from tools.custom_tools import scrape_huggingface_models, save_data
from config import Config

class MainAgent(Agent):
    """
    Main agent for scraping Hugging Face models.
    """
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.version = "1.0.0"

    async def run(self):
        """
        Executes the main workflow of the agent.
        """
        try:
            self.logger.info("Starting Hugging Face scraping agent...")

            # Scrape the models
            models_data = await scrape_huggingface_models(
                url=self.config.huggingface_url,
                max_pages=self.config.max_pages,
                request_interval=self.config.request_interval,
                user_agent=self.config.user_agent
            )

            # Save the scraped data
            await save_data(
                data=models_data,
                output_dir=self.config.output_dir,
                output_format=self.config.output_format
            )

            self.logger.info("Hugging Face scraping agent completed successfully.")
            self.case_resolved("Scraping and saving completed successfully.")

        except Exception as e:
            self.logger.exception("An error occurred during the agent's execution:")
            self.case_not_resolved(f"An error occurred: {e}")