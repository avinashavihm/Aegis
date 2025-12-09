"""
Meta tools for tool management
"""

import json
import os
from aegis.registry import register_tool, registry
from aegis.environment.local_env import LocalEnv


@register_tool("list_tools")
def list_tools(context_variables: dict = None) -> str:
    """
    List all plugin tools in Aegis.
    
    Returns:
        A JSON string with information about all plugin tools.
    """
    try:
        tools_info = registry.display_plugin_tools_info
        return json.dumps(tools_info, indent=2)
    except Exception as e:
        return f"[ERROR] Failed to list tools. Error: {str(e)}"


@register_tool("create_tool")
def create_tool(
    tool_name: str,
    tool_code: str,
    context_variables: dict = None
) -> str:
    """
    Create a new plugin tool.
    
    Args:
        tool_name: The name of the tool.
        tool_code: The Python code for the tool (must include @register_plugin_tool decorator).
    """
    env: LocalEnv = context_variables.get("code_env") if context_variables else LocalEnv()
    workspace_path = env.local_root
    tools_dir = os.path.join(workspace_path, "tools")
    os.makedirs(tools_dir, exist_ok=True)
    
    # Ensure the code includes the register decorator
    if "from aegis.registry import register_plugin_tool" not in tool_code:
        tool_code = "from aegis.registry import register_plugin_tool\n" + tool_code
    
    tool_file = os.path.join(tools_dir, f"{tool_name}.py")
    
    try:
        result = env.create_file(tool_file.replace(workspace_path + "/", ""), tool_code)
        if result.get("status") != 0:
            return f"[ERROR] Failed to create tool. Error: {result.get('message', 'Unknown error')}"
        
        # Try to import the tool to validate it
        import sys
        sys.path.insert(0, tools_dir)
        try:
            __import__(tool_name)
            return f"[SUCCESS] Successfully created tool: {tool_name} in {tool_file}"
        except Exception as e:
            return f"[WARNING] Tool file created but validation failed: {str(e)}. File: {tool_file}"
    except Exception as e:
        return f"[ERROR] Failed to create tool. Error: {str(e)}"


@register_tool("delete_tool")
def delete_tool(tool_name: str, context_variables: dict = None) -> str:
    """
    Delete a plugin tool.
    
    Args:
        tool_name: The name of the tool to delete.
    """
    try:
        tools_info = json.loads(list_tools(context_variables))
        if tool_name not in tools_info:
            return f"[ERROR] The tool {tool_name} does not exist."
        
        tool_info = tools_info[tool_name]
        tool_path = tool_info.get('file_path', '')
        
        if tool_path and os.path.exists(tool_path):
            os.remove(tool_path)
            return f"[SUCCESS] Successfully deleted tool: {tool_name}"
        else:
            return f"[ERROR] Tool file not found: {tool_path}"
    except Exception as e:
        return f"[ERROR] Failed to delete tool. Error: {str(e)}"


@register_tool("run_tool")
def run_tool(
    tool_name: str,
    tool_args: dict,
    context_variables: dict = None
) -> str:
    """
    Run a plugin tool.
    
    Args:
        tool_name: The name of the tool to run.
        tool_args: Dictionary of arguments for the tool.
    """
    try:
        if tool_name in registry.plugin_tools:
            tool_func = registry.plugin_tools[tool_name]
            result = tool_func(**tool_args, context_variables=context_variables)
            return str(result)
        else:
            return f"[ERROR] Tool {tool_name} not found in registry."
    except Exception as e:
        return f"[ERROR] Failed to run tool. Error: {str(e)}"

