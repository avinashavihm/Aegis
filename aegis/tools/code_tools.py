"""
Code execution tools
"""

from aegis.registry import register_tool
from aegis.environment.local_env import LocalEnv


@register_tool("execute_python")
def execute_python(code: str, context_variables: dict = None) -> str:
    """
    Execute Python code.
    
    Args:
        code: Python code to execute.
    """
    code_env: LocalEnv = context_variables.get("code_env") if context_variables else None
    if not code_env:
        code_env = LocalEnv()
    result = code_env.run_python(code)
    if result["status"] == 0:
        return result["result"]
    else:
        return f"Error: {result['result']}"


@register_tool("execute_command")
def execute_command(command: str, context_variables: dict = None) -> str:
    """
    Execute a shell command.
    
    Args:
        command: Shell command to execute.
    """
    code_env: LocalEnv = context_variables.get("code_env") if context_variables else None
    if not code_env:
        code_env = LocalEnv()
    result = code_env.run_command(command)
    if result["status"] == 0:
        return result["result"]
    else:
        return f"Error (exit code {result['status']}): {result['result']}"


@register_tool("run_script")
def run_script(script_path: str, args: str = "", context_variables: dict = None) -> str:
    """
    Run a script file.
    
    Args:
        script_path: Path to the script file.
        args: Arguments to pass to the script.
    """
    code_env: LocalEnv = context_variables.get("code_env") if context_variables else None
    if not code_env:
        code_env = LocalEnv()
    command = f"python {script_path} {args}".strip()
    result = code_env.run_command(command)
    if result["status"] == 0:
        return result["result"]
    else:
        return f"Error (exit code {result['status']}): {result['result']}"

