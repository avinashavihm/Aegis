import asyncio
import logging

from aegis.types import Agent
from aegis.tools import case_resolved, case_not_resolved
from config import Config
from utils.helpers import generate_agent_name

logger = logging.getLogger(__name__)


class BookingAgent(Agent):
    """
    Agent responsible for booking flights, hotels, and activities
    based on the travel plan.
    """

    def __init__(self, config: Config):
        super().__init__(
            name=generate_agent_name("Booking"),
            llm_model=config.default_llm_model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        self.config = config

    async def run(self, travel_plan: str) -> str:
        """
        Executes the booking process based on the travel plan.

        This is a simplified example.  A real booking agent would
        integrate with actual booking APIs.
        """
        try:
            logger.info(f"Booking based on plan: {travel_plan}")

            # Simulate booking confirmation
            booking_confirmation = f"Successfully booked travel plan: {travel_plan}. Confirmation number: BOOK12345"

            await case_resolved(booking_confirmation)
            return booking_confirmation

        except Exception as e:
            logger.exception(f"Error during booking: {e}")
            await case_not_resolved(f"Booking failed: {e}")
            return f"Booking failed: {e}"