"""
Core type definitions for Aegis
"""

from typing import List, Callable, Union, Optional
from pydantic import BaseModel
from litellm.types.utils import ChatCompletionMessageToolCall, Function, Message

AgentFunction = Callable[[], Union[str, "Agent", dict]]


class Agent(BaseModel):
    """Agent definition with instructions, model, and tools"""
    name: str = "Agent"
    model: str = "gpt-4o"
    instructions: Union[str, Callable[[dict], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    tool_choice: Optional[str] = None
    parallel_tool_calls: bool = False
    examples: Union[List, Callable[[dict], List]] = []
    handle_mm_func: Optional[Callable] = None
    agent_teams: dict = {}


class Response(BaseModel):
    """Response from agent execution"""
    messages: List = []
    agent: Optional[Agent] = None
    context_variables: dict = {}


class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.
    
    Attributes:
        value: The result value as a string
        agent: The agent instance, if applicable
        context_variables: A dictionary of context variables
        image: Base64 encoded image, if applicable
    """
    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = {}
    image: Optional[str] = None  # base64 encoded image

