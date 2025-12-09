"""
File Agent for file operations
"""

from aegis.registry import register_agent
from aegis.types import Agent, Result
from aegis.tools.file_tools import read_file, write_file, list_files, search_files
from aegis.tools.inner import case_resolved, case_not_resolved


@register_agent(name="File Agent", func_name="get_file_agent")
def get_file_agent(model: str) -> Agent:
    """
    File Agent for handling file operations.
    
    Args:
        model: The model to use for the agent.
    """
    instructions = """You are a File Agent specialized in file operations.
You can help users:
- Read files from the workspace
- Write/create files in the workspace
- List files in directories
- Search for files matching patterns

Always use the appropriate tools to complete file-related tasks. When you've completed the task, use case_resolved to indicate success.
If you cannot complete the task after trying your best, use case_not_resolved."""
    
    tools = [read_file, write_file, list_files, search_files, case_resolved, case_not_resolved]
    
    return Agent(
        name="File Agent",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required",
        parallel_tool_calls=False
    )

