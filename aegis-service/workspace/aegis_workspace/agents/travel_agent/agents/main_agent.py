import logging
from aegis.types import Agent
from agents.planning_agent import PlanningAgent
from agents.research_agent import ResearchAgent
from agents.booking_agent import BookingAgent
from utils.helpers import retry
from config import Config

class MainAgent(Agent):
    """
    The main agent responsible for orchestrating the travel planning process.
    """

    def __init__(self, config: Config, name="MainAgent", description="Orchestrates travel planning"):
        super().__init__(name=name, description=description)
        self.config = config
        self.planning_agent = PlanningAgent(config=config)
        self.research_agent = ResearchAgent(config=config)
        self.booking_agent = BookingAgent(config=config)
        self.logger = logging.getLogger(__name__)

    @retry(max_retries=3, delay=2)
    def execute_task(self, task: str) -> str:
        """
        Executes the main travel planning task by orchestrating other agents.
        """
        try:
            self.logger.info(f"Executing main task: {task}")

            # 1. Planning: Get the travel plan from the PlanningAgent
            plan = self.planning_agent.create_travel_plan(task)
            self.logger.info(f"Generated travel plan: {plan}")

            # 2. Research: Research specific aspects of the plan using the ResearchAgent
            research_results = self.research_agent.research_travel_details(plan)
            self.logger.info(f"Research results: {research_results}")

            # 3. Booking: Book flights, hotels, etc. using the BookingAgent
            booking_confirmation = self.booking_agent.book_travel(research_results)
            self.logger.info(f"Booking confirmation: {booking_confirmation}")

            # 4. Collate results and return
            final_result = f"Travel Plan: {plan}\nResearch Results: {research_results}\nBooking Confirmation: {booking_confirmation}"
            return final_result

        except Exception as e:
            self.logger.exception(f"Error during task execution: {e}")
            raise

    def case_resolved(self, solution: str) -> str:
        """
        Returns a message indicating the case is resolved.
        """
        return f"Case resolved: {solution}"

    def case_not_resolved(self, reason: str) -> str:
        """
        Returns a message indicating the case is not resolved.
        """
        return f"Case not resolved: {reason}"