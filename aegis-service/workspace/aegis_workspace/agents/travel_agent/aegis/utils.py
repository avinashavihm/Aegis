"""
Utility functions for Aegis
"""

import json
import inspect
from typing import Callable, Any, Dict, List
from aegis.types import AgentFunction


def function_to_json(func: Callable) -> Dict[str, Any]:
    """
    Convert a Python function to OpenAI function calling format.
    
    Args:
        func: The function to convert
        
    Returns:
        Dictionary in OpenAI function calling format
    """
    sig = inspect.signature(func)
    docstring = inspect.getdoc(func) or ""
    
    # Parse docstring for parameter descriptions
    params = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name == "context_variables":
            continue  # Skip context_variables, it's injected automatically
        
        param_info = {"type": "string"}  # Default type
        
        # Try to infer type from annotation
        if param.annotation != inspect.Parameter.empty:
            ann_str = str(param.annotation)
            if "int" in ann_str:
                param_info["type"] = "integer"
            elif "float" in ann_str:
                param_info["type"] = "number"
            elif "bool" in ann_str:
                param_info["type"] = "boolean"
            elif "list" in ann_str.lower() or "List" in ann_str:
                param_info["type"] = "array"
                param_info["items"] = {"type": "string"}
        
        # Check if required (no default value)
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
        
        params[param_name] = param_info
    
    # Extract description from docstring
    description = ""
    if docstring:
        # Try to extract main description (first paragraph)
        lines = docstring.strip().split('\n')
        description = lines[0].strip()
    
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required
            }
        }
    }


def debug_print(debug: bool, *args, **kwargs):
    """Print debug information if debug is True"""
    if debug:
        title = kwargs.get('title', 'DEBUG')
        color = kwargs.get('color', 'blue')
        print(f"[{title}]", *args)


def merge_chunk(message: dict, delta: dict):
    """Merge a delta chunk into a message"""
    if "content" in delta:
        message["content"] = message.get("content", "") + delta.get("content", "")
    if "tool_calls" in delta:
        if "tool_calls" not in message:
            message["tool_calls"] = {}
        for tool_call in delta.get("tool_calls", []):
            idx = tool_call.get("index", 0)
            if idx not in message["tool_calls"]:
                message["tool_calls"][idx] = {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""}
                }
            if "id" in tool_call:
                message["tool_calls"][idx]["id"] = tool_call["id"]
            if "function" in tool_call:
                func = tool_call["function"]
                if "name" in func:
                    message["tool_calls"][idx]["function"]["name"] = func["name"]
                if "arguments" in func:
                    message["tool_calls"][idx]["function"]["arguments"] += func["arguments"]


def pretty_print_messages(messages: List[dict]):
    """Pretty print messages for debugging"""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        print(f"[{role.upper()}] {content[:100]}..." if len(str(content)) > 100 else f"[{role.upper()}] {content}")

