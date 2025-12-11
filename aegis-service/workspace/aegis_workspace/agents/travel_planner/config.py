import os
from dataclasses import dataclass

@dataclass
class Config:
    """
    Configuration class for the Travel Planner Agent.
    """
    openai_api_key: str = os.environ.get("OPENAI_API_KEY")
    serpapi_api_key: str = os.environ.get("SERPAPI_API_KEY")
    google_maps_api_key: str = os.environ.get("GOOGLE_MAPS_API_KEY")
    default_llm_model: str = "gpt-4-turbo-preview"  # Updated model name
    temperature: float = 0.7
    max_tokens: int = 2000

    def __post_init__(self):
        """
        Validate that required environment variables are set.
        """
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set.")

        # Optional API keys, but log a warning if not set
        if not self.serpapi_api_key:
            print("Warning: SERPAPI_API_KEY environment variable not set. Search functionality will be limited.")

        if not self.google_maps_api_key:
            print("Warning: GOOGLE_MAPS_API_KEY environment variable not set. Distance calculations will be limited.")