"""
Tool usage memory for tracking tool calls and results
"""

from typing import Dict, List, Optional
from datetime import datetime
import json


class ToolMemory:
    """Memory system for tracking tool usage"""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.tool_calls: List[Dict] = []
        self.tool_results: Dict[str, List[Dict]] = {}
    
    def record_tool_call(self, tool_name: str, args: dict, result: str, success: bool = True):
        """Record a tool call"""
        record = {
            "tool_name": tool_name,
            "args": args,
            "result": result[:1000] if len(result) > 1000 else result,  # Truncate long results
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        self.tool_calls.append(record)
        if len(self.tool_calls) > self.max_history:
            self.tool_calls.pop(0)
        
        # Store by tool name
        if tool_name not in self.tool_results:
            self.tool_results[tool_name] = []
        self.tool_results[tool_name].append(record)
        if len(self.tool_results[tool_name]) > 20:  # Keep last 20 per tool
            self.tool_results[tool_name].pop(0)
    
    def get_tool_history(self, tool_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get tool call history"""
        if tool_name:
            return self.tool_results.get(tool_name, [])[-limit:]
        return self.tool_calls[-limit:]
    
    def get_tool_summary(self, tool_name: str) -> str:
        """Get a summary of tool usage"""
        history = self.tool_results.get(tool_name, [])
        if not history:
            return f"No usage history for {tool_name}"
        
        success_count = sum(1 for h in history if h["success"])
        total_count = len(history)
        
        return f"Tool {tool_name}: Used {total_count} times, {success_count} successful"
    
    def clear(self):
        """Clear all memory"""
        self.tool_calls = []
        self.tool_results = {}


# Global tool memory instance
tool_memory = ToolMemory()

