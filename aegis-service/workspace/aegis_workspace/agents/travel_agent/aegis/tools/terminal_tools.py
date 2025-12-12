"""
Terminal operation tools
"""

from aegis.registry import register_tool
from aegis.environment.local_env import LocalEnv


@register_tool("run_command")
def run_command(command: str, context_variables: dict = None) -> str:
    """
    Run a terminal command.
    
    Args:
        command: Command to execute in the terminal.
    """
    code_env: LocalEnv = context_variables.get("code_env") if context_variables else None
    if not code_env:
        code_env = LocalEnv()
    result = code_env.run_command(command)
    if result["status"] == 0:
        return result["result"]
    else:
        return f"Error (exit code {result['status']}): {result['result']}"


@register_tool("list_directory")
def list_directory(directory: str = ".", context_variables: dict = None) -> str:
    """
    List contents of a directory.
    
    Args:
        directory: Directory path (relative to workspace).
    """
    code_env: LocalEnv = context_variables.get("code_env") if context_variables else None
    if not code_env:
        code_env = LocalEnv()
    result = code_env.run_command(f"ls -la {directory}")
    if result["status"] == 0:
        return result["result"]
    else:
        return f"Error: {result['result']}"

