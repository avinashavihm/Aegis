import asyncio
import logging

from aegis.types import Agent
from aegis.tools import read_file, write_file, execute_python, case_resolved, case_not_resolved
from tools.custom_tools import search_internet
from config import Config
from utils.helpers import generate_agent_name

logger = logging.getLogger(__name__)

class ResearchAgent(Agent):
    """
    Agent responsible for researching travel destinations,
    accommodations, and activities.
    """

    def __init__(self, config: Config):
        super().__init__(
            name=generate_agent_name("Research"),
            llm_model=config.default_llm_model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        self.config = config

    async def run(self, task: str) -> str:
        """
        Executes the research task and returns the findings.
        """
        try:
            logger.info(f"Researching: {task}")

            # Initial search query.  Improve based on results
            search_query = f"Travel information for {task}"
            search_results = await search_internet(query=search_query, serpapi_api_key=self.config.serpapi_api_key)

            if not search_results:
                search_query = f"Things to do and places to stay in {task}"
                search_results = await search_internet(query=search_query, serpapi_api_key=self.config.serpapi_api_key)

            if not search_results:
                 await case_not_resolved("Could not find any information.  Please check the task and try again.")
                 return "No information found."


            # Refine search based on initial results (example)
            refined_query = f"Top attractions and hidden gems in {task} based on {search_results[:200]}" # Limit to 200 chars
            refined_results = await search_internet(query=refined_query, serpapi_api_key=self.config.serpapi_api_key)

            # Combine results
            combined_results = search_results + "\n" + refined_results

            await case_resolved(combined_results) # Important: Mark as resolved
            return combined_results

        except Exception as e:
            logger.exception(f"Error during research: {e}")
            await case_not_resolved(f"Research failed: {e}")
            return f"Research failed: {e}"