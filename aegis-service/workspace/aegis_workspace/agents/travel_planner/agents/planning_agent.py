import asyncio
import logging

from aegis.types import Agent
from aegis.tools import read_file, write_file, execute_python, case_resolved, case_not_resolved
from config import Config
from utils.helpers import generate_agent_name

logger = logging.getLogger(__name__)


class PlanningAgent(Agent):
    """
    Agent responsible for creating a detailed travel plan based on
    research results.
    """

    def __init__(self, config: Config):
        super().__init__(
            name=generate_agent_name("Planning"),
            llm_model=config.default_llm_model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        self.config = config

    async def run(self, research_results: str) -> str:
        """
        Generates a travel plan based on the research results.
        """
        try:
            logger.info(f"Planning based on research: {research_results}")

            # Prompt to generate a travel plan
            prompt = f"""
            Based on the following research results:

            {research_results}

            Create a detailed travel plan, including:
            - A daily itinerary with specific activities and locations.
            - Recommendations for accommodations (hotels, etc.).
            - Transportation options (flights, trains, car rentals).
            - Estimated costs for each item.

            The plan should be well-structured and easy to follow.
            """

            travel_plan = await self.llm(prompt)

            await case_resolved(travel_plan)
            return travel_plan

        except Exception as e:
            logger.exception(f"Error during planning: {e}")
            await case_not_resolved(f"Planning failed: {e}")
            return f"Planning failed: {e}"