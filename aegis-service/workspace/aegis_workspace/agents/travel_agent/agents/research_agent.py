import logging
import os
from aegis.types import Agent
from config import Config
from litellm import completion
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
                # Fallback: return mock research
                mock_research = f"""Mock Research Results for: {travel_plan}

Since no API keys are configured, here's sample research:

**Recommended Hotels:**
- Hotel A: $200/night, city center
- Hotel B: $150/night, near airport

**Flight Options:**
- Airline X: $500 round trip
- Airline Y: $450 round trip

**Activities:**
- Museum visit: $25
- City tour: $40

**Note:** Configure API keys for real research results."""
                self.logger.warning("No API keys configured, returning mock research")
                return mock_research

            # Example implementation: Research using LLM
            prompt = f"Research and provide specific recommendations for hotels, flights, and activities for this travel plan: {travel_plan}. Include estimated costs and booking links if possible."

            # Use litellm for LLM calls
            response = completion(
                model=self.config.planning_agent_model,  # Reuse planning model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            research_results = response.choices[0].message.content.strip()

            self.logger.info(f"Research results: {research_results}")
            return research_results

        except Exception as e:
            self.logger.exception(f"Error researching travel details: {e}")
            # Fallback mock research
            fallback_research = f"""Fallback Research for: {travel_plan}

**Basic Recommendations:**
- Check major hotel booking sites
- Compare flight prices on airline websites
- Look for local tours and activities

**Error Details:** {str(e)}"""
            return fallback_research