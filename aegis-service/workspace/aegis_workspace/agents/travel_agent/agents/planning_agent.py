import logging
from aegis.types import Agent
from config import Config
from aegis.tools import execute_python
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

            # Example implementation: Generate a plan using a simple prompt
            prompt = f"Create a detailed travel plan for the following request: {task}. Include destinations, activities, and estimated duration. Be specific and provide concrete suggestions."

            # Execute Python code to call OpenAI (replace with actual implementation)
            code = f"""
import openai
openai.api_key = "{self.config.openai_api_key}"
response = openai.Completion.create(
    engine="{self.config.planning_agent_model}",
    prompt="{prompt}",
    max_tokens=200,
    n=1,
    stop=None,
    temperature=0.7,
)
plan = response.choices[0].text.strip()
"""
            result = execute_python(code) # Use aegis tool to execute python
            plan = result

            self.logger.info(f"Generated travel plan: {plan}")
            return plan

        except Exception as e:
            self.logger.exception(f"Error creating travel plan: {e}")
            raise