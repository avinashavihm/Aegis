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
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        self.together_api_key = os.getenv("TOGETHER_API_KEY")

        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.travel_api_key = os.getenv("TRAVEL_API_KEY")
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        self.default_city = os.getenv("DEFAULT_CITY", "London")

        # Add other configuration parameters as needed
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))

        # Agent specific configurations (example). Choose available provider if set.
        self.planning_agent_model = os.getenv("PLANNING_AGENT_MODEL")
        self.booking_agent_model = os.getenv("BOOKING_AGENT_MODEL")

        # Choose an available model if none provided
        provider_models = [
            (self.openai_api_key, "gpt-4o"),
            (self.anthropic_api_key, "claude-3-opus-20240229"),
            (self.gemini_api_key, "gemini-1.5-pro"),
            (self.groq_api_key, "llama-3-70b"),
            (self.mistral_api_key, "mistral-large-latest"),
            (self.cohere_api_key, "command-r-plus"),
            (self.together_api_key, "meta-llama/Meta-Llama-3-70B-Instruct-Turbo"),
        ]
        fallback = None
        for key, model in provider_models:
            if key:
                fallback = model
                break
        if not self.planning_agent_model:
            self.planning_agent_model = fallback or "gpt-4o"
        if not self.booking_agent_model:
            self.booking_agent_model = fallback or "gpt-3.5-turbo"

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