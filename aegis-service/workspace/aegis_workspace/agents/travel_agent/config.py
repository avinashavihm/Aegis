import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Configuration class for the Travel Agent application.
    """

    def __init__(self):
        """
        Initializes the configuration settings.
        """
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.travel_api_key = os.getenv("TRAVEL_API_KEY")
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        self.default_city = os.getenv("DEFAULT_CITY", "London")

        # Add other configuration parameters as needed
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))

        # Agent specific configurations (example)
        self.planning_agent_model = os.getenv("PLANNING_AGENT_MODEL", "gpt-4")
        self.booking_agent_model = os.getenv("BOOKING_AGENT_MODEL", "gpt-3.5-turbo")

        self.validate_config()

    def validate_config(self):
        """
        Validates the configuration settings.  Raises ValueError if a required
        configuration is missing or invalid.
        """
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.log_level}")

        if self.max_retries < 0:
            raise ValueError("MAX_RETRIES must be a non-negative integer.")

        if self.retry_delay < 0:
            raise ValueError("RETRY_DELAY must be a non-negative integer.")