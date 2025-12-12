"""
Code Agent for code execution
"""

from aegis.registry import register_agent
from aegis.types import Agent
from aegis.tools.code_tools import execute_python, execute_command, run_script
from aegis.tools.file_tools import read_file, write_file
from aegis.tools.inner import case_resolved, case_not_resolved


@register_agent(name="Code Agent", func_name="get_code_agent")
def get_code_agent(model: str) -> Agent:
    """
    Code Agent for handling code execution and programming tasks.
    
    Args:
        model: The model to use for the agent.
    """
    instructions = """You are a Code Agent specialized in code execution and programming tasks.
You can help users:
- Execute Python code (including importing and using ANY external libraries)
- Run shell commands (including pip install for dependencies)
- Execute script files
- Read and write files (for code files)

IMPORTANT: You can use execute_python to run Python code that imports and uses ANY external library.
For example, if you need youtube_transcript_api, you can use execute_python with code like:
```python
from youtube_transcript_api import YouTubeTranscriptApi
# ... use the library
```

If a library is not installed, use execute_command to install it first (e.g., pip install youtube_transcript_api).

Always use the appropriate tools to complete programming tasks. Be careful with code execution - validate code before executing.
When you've completed the task, use case_resolved to indicate success.
If you cannot complete the task after trying your best, use case_not_resolved."""
    
    tools = [execute_python, execute_command, run_script, read_file, write_file, case_resolved, case_not_resolved]
    
    return Agent(
        name="Code Agent",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required",
        parallel_tool_calls=False
    )

