import logging
from aegis.types import Agent
from config import Config
from aegis.tools import execute_python
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

            # Example implementation:  Simulate booking using the research results
            prompt = f"Based on the following research results, create a booking confirmation: {research_results}.  Include flight details, hotel information, and activity reservations.  If details are missing, make reasonable assumptions."

            # Execute Python code to call OpenAI (replace with actual implementation)
            code = f"""
import openai
openai.api_key = "{self.config.openai_api_key}"
response = openai.Completion.create(
    engine="{self.config.booking_agent_model}",
    prompt="{prompt}",
    max_tokens=200,
    n=1,
    stop=None,
    temperature=0.7,
)
booking_confirmation = response.choices[0].text.strip()
"""
            result = execute_python(code)
            booking_confirmation = result

            self.logger.info(f"Booking confirmation: {booking_confirmation}")
            return booking_confirmation

        except Exception as e:
            self.logger.exception(f"Error booking travel: {e}")
            raise