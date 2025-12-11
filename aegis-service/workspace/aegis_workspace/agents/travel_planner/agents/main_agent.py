import asyncio
import logging

from aegis.types import Agent
from aegis.tools import case_resolved, case_not_resolved

from agents.research_agent import ResearchAgent
from agents.booking_agent import BookingAgent
from agents.planning_agent import PlanningAgent
from config import Config
from utils.helpers import generate_agent_name

logger = logging.getLogger(__name__)


class MainAgent(Agent):
    """
    The main orchestrator agent for the travel planner.  It delegates tasks
    to specialized agents for research, planning, and booking.
    """

    def __init__(self, config: Config):
        super().__init__(
            name=generate_agent_name("Main"),
            llm_model=config.default_llm_model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        self.config = config
        self.research_agent = ResearchAgent(config=config)
        self.planning_agent = PlanningAgent(config=config)
        self.booking_agent = BookingAgent(config=config)

    async def run(self, task: str):
        """
        Orchestrates the travel planning process.
        """
        try:
            logger.info(f"Main agent received task: {task}")

            # 1. Research Phase
            research_results = await self.research_agent.run(task)
            logger.info(f"Research agent returned: {research_results}")

            # 2. Planning Phase
            plan = await self.planning_agent.run(research_results)  # Pass research results
            logger.info(f"Planning agent returned: {plan}")

            # 3. Booking Phase
            booking_confirmation = await self.booking_agent.run(plan)  # Pass the plan
            logger.info(f"Booking agent returned: {booking_confirmation}")

            # 4. Final Result
            final_result = f"Travel plan finalized and booked! Confirmation: {booking_confirmation}"
            await case_resolved(final_result)
            return final_result

        except Exception as e:
            logger.exception(f"Error during travel planning: {e}")
            await case_not_resolved(f"An error occurred during travel planning: {e}")
            return None