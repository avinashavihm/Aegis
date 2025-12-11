import os
from dataclasses import dataclass

@dataclass
class Config:
    """
    Configuration class for the Hugging Face web scraping agent.
    """
    huggingface_url: str = "https://huggingface.co/models"
    output_dir: str = "output"
    output_format: str = "json"  # json, csv, txt
    max_pages: int = 5
    request_interval: float = 2.0  # Time in seconds between requests
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __post_init__(self):
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)