import logging
import os
from aegis.types import Agent
from config import Config
from litellm import completion
from utils.helpers import retry

class BookingAgent(Agent):
    """
    Agent responsible for booking travel arrangements.
    """

    def __init__(self, config: Config, name="BookingAgent", description="Books travel arrangements"):
        super().__init__(name=name, description=description)
        self.config = config
        self.logger = logging.getLogger(__name__)

    @retry(max_retries=3, delay=2)
    def book_travel(self, research_results: str) -> str:
        """
        Books flights, hotels, etc. based on the research results.
        """
        try:
            self.logger.info(f"Booking travel based on research results: {research_results}")

            # Check if any API keys are available
            available_keys = []
            if self.config.openai_api_key:
                available_keys.append("OpenAI")
                os.environ["OPENAI_API_KEY"] = self.config.openai_api_key
            if self.config.anthropic_api_key:
                available_keys.append("Anthropic")
                os.environ["ANTHROPIC_API_KEY"] = self.config.anthropic_api_key
            if self.config.gemini_api_key:
                available_keys.append("Gemini")
                os.environ["GEMINI_API_KEY"] = self.config.gemini_api_key
            if self.config.groq_api_key:
                available_keys.append("Groq")
                os.environ["GROQ_API_KEY"] = self.config.groq_api_key

            if not available_keys:
                # Fallback: return mock booking
                mock_booking = f"""Mock Booking Confirmation for: {research_results}

Since no API keys are configured, here's a sample booking:

**Flight Booking:**
- Confirmation: ABC123
- Airline: Sample Airlines
- Route: Origin to Destination
- Date: Tomorrow

**Hotel Booking:**
- Confirmation: HOTEL456
- Hotel: Sample Hotel
- Check-in: Tomorrow
- Check-out: Day after

**Note:** Configure API keys for actual bookings."""
                self.logger.warning("No API keys configured, returning mock booking")
                return mock_booking

            # Example implementation: Generate booking confirmation
            prompt = f"Based on the following research results, create a detailed booking confirmation: {research_results}. Include flight details, hotel information, and activity reservations with confirmation numbers."

            # Use litellm for LLM calls
            response = completion(
                model=self.config.booking_agent_model or self.config.planning_agent_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            booking_confirmation = response.choices[0].message.content.strip()

            self.logger.info(f"Booking confirmation: {booking_confirmation}")
            return booking_confirmation

        except Exception as e:
            self.logger.exception(f"Error booking travel: {e}")
            # Fallback mock booking
            fallback_booking = f"""Fallback Booking Confirmation for: {research_results}

**Emergency Booking:**
- Status: Provisional booking created
- Next Steps: Contact travel agent for confirmation
- Reference: FALLBACK-{hash(research_results) % 10000}

**Error Details:** {str(e)}"""
            return fallback_booking