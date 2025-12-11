import logging
from aegis.types import Agent
from config import Config
from aegis.tools import execute_python
from utils.helpers import retry

class ResearchAgent(Agent):
    """
    Agent responsible for researching travel details.
    """

    def __init__(self, config: Config, name="ResearchAgent", description="Researches travel details"):
        super().__init__(name=name, description=description)
        self.config = config
        self.logger = logging.getLogger(__name__)

    @retry(max_retries=3, delay=2)
    def research_travel_details(self, travel_plan: str) -> str:
        """
        Researches specific details related to the travel plan.
        """
        try:
            self.logger.info(f"Researching travel details for plan: {travel_plan}")

            # Example implementation: Research using a search engine API
            prompt = f"Research the best hotels, flights, and activities for the following travel plan: {travel_plan}.  Provide specific recommendations and links to relevant websites."

            # Execute Python code to call SerpAPI (replace with actual implementation)
            code = f"""
import os
from serpapi import GoogleSearch

params = {{
  "api_key": "{self.config.serpapi_api_key}",
  "engine": "google",
  "q": "{prompt}",
  "google_domain": "google.com"
}}

search = GoogleSearch(params)
results = search.get_dict()
organic_results = results.get('organic_results', [])
research_results = str(organic_results) #stringify for return

"""
            result = execute_python(code)
            research_results = result

            self.logger.info(f"Research results: {research_results}")
            return research_results

        except Exception as e:
            self.logger.exception(f"Error researching travel details: {e}")
            raise