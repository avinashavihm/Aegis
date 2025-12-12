"""
Tool utilities
"""

from typing import Callable, Dict, Any
from aegis.utils import function_to_json


def validate_tool(func: Callable) -> bool:
    """Validate that a function can be used as a tool"""
    try:
        function_to_json(func)
        return True
    except Exception:
        return False

