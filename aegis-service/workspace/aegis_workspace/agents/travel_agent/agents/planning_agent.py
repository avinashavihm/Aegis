import logging
import os
from aegis.types import Agent
from config import Config
from litellm import completion
from utils.helpers import retry

class PlanningAgent(Agent):
    """
    Agent responsible for creating the initial travel plan.
    """

    def __init__(self, config: Config, name="PlanningAgent", description="Creates initial travel plans"):
        super().__init__(name=name, description=description)
        self.config = config
        self.logger = logging.getLogger(__name__)

    @retry(max_retries=3, delay=2)
    def create_travel_plan(self, task: str) -> str:
        """
        Creates a travel plan based on the given task.
        """
        try:
            self.logger.info(f"Creating travel plan for task: {task}")

            # Check if any API keys are available
            available_keys = []
            model_has_key = False

            if self.config.openai_api_key:
                available_keys.append("OpenAI")
                os.environ["OPENAI_API_KEY"] = self.config.openai_api_key
                if "gpt" in self.config.planning_agent_model or "openai" in self.config.planning_agent_model:
                    model_has_key = True
            if self.config.anthropic_api_key:
                available_keys.append("Anthropic")
                os.environ["ANTHROPIC_API_KEY"] = self.config.anthropic_api_key
                if "claude" in self.config.planning_agent_model or "anthropic" in self.config.planning_agent_model:
                    model_has_key = True
            if self.config.gemini_api_key:
                available_keys.append("Gemini")
                os.environ["GEMINI_API_KEY"] = self.config.gemini_api_key
                if "gemini" in self.config.planning_agent_model:
                    model_has_key = True
            if self.config.groq_api_key:
                available_keys.append("Groq")
                os.environ["GROQ_API_KEY"] = self.config.groq_api_key
                if "llama" in self.config.planning_agent_model or "groq" in self.config.planning_agent_model:
                    model_has_key = True

            if not available_keys or not model_has_key:
                # Fallback: return a mock plan for testing
                mock_plan = f"""Mock Travel Plan for: {task}

Since no API keys are configured or the selected model doesn't have credentials, here's a sample travel plan:

**Destination:** Paris, France
**Duration:** 3-5 days
**Activities:**
- Visit Eiffel Tower
- Louvre Museum
- Seine River cruise
- Montmartre district

**Note:** Configure API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY) for actual AI-generated plans.
**Selected Model:** {self.config.planning_agent_model}
**Available Keys:** {available_keys}"""
                self.logger.warning(f"No valid API key for model {self.config.planning_agent_model}, returning mock plan")
                return mock_plan

            # Example implementation: Generate a plan using a simple prompt
            prompt = f"Create a detailed travel plan for the following request: {task}. Include destinations, activities, and estimated duration. Be specific and provide concrete suggestions."

            # Try to use litellm for LLM calls
            try:
                self.logger.info(f"Attempting API call with model: {self.config.planning_agent_model}")
                response = completion(
                    model=self.config.planning_agent_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.7,
                )
                plan = response.choices[0].message.content.strip()
                self.logger.info(f"Generated travel plan: {plan}")
                return plan
            except Exception as api_error:
                self.logger.warning(f"API call failed for model {self.config.planning_agent_model}: {api_error}")
                print(f"DEBUG: API call failed, using fallback. Error: {api_error}")
                # Fall back to mock plan
                mock_plan = f"""Mock Travel Plan for: {task}

The AI service is not properly configured. Here's a sample travel plan:

**Destination:** Paris, France
**Duration:** 3-5 days
**Activities:**
- Visit Eiffel Tower
- Louvre Museum
- Seine River cruise
- Montmartre district

**API Error:** {str(api_error)}
**Selected Model:** {self.config.planning_agent_model}
**Available Keys:** {available_keys}"""
                print(f"DEBUG: Returning mock plan: {mock_plan[:100]}...")
                return mock_plan

        except Exception as e:
            self.logger.exception(f"Unexpected error creating travel plan: {e}")
            # Fallback mock plan
            fallback_plan = f"""Fallback Travel Plan for: {task}

Due to unexpected issues, here's a basic travel plan:

**Basic Itinerary:**
- Day 1: Arrival and city exploration
- Day 2: Visit main attractions
- Day 3: Local experiences and departure

**Error Details:** {str(e)}"""
            return fallback_plan