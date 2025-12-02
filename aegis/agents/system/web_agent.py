"""
Web Agent for web browsing
"""

from aegis.registry import register_agent
from aegis.types import Agent
from aegis.tools.web_tools import fetch_url, search_web, extract_content
from aegis.tools.inner import case_resolved, case_not_resolved


@register_agent(name="Web Agent", func_name="get_web_agent")
def get_web_agent(model: str) -> Agent:
    """
    Web Agent for handling web browsing operations.
    
    Args:
        model: The model to use for the agent.
    """
    instructions = """You are a Web Agent specialized in web browsing and information retrieval.
You can help users:
- Fetch content from URLs
- Search the web (when search API is available)
- Extract text content from HTML

Always use the appropriate tools to complete web-related tasks. When you've completed the task, use case_resolved to indicate success.
If you cannot complete the task after trying your best, use case_not_resolved."""
    
    tools = [fetch_url, search_web, extract_content, case_resolved, case_not_resolved]
    
    return Agent(
        name="Web Agent",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required",
        parallel_tool_calls=False
    )

