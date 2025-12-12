"""
Logging utilities for Aegis
"""

import logging
import sys
from typing import Optional
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


class AegisLogger:
    """Logger for Aegis with rich console output"""
    
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path
        self.console = Console()
        
        # Set up file logging if path provided
        if log_path:
            Path(log_path).parent.mkdir(parents=True, exist_ok=True)
            self.file_logger = logging.getLogger("aegis")
            self.file_logger.setLevel(logging.DEBUG)
            handler = logging.FileHandler(log_path)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.file_logger.addHandler(handler)
        else:
            self.file_logger = None
    
    def info(self, *args, title: str = "INFO", color: str = "blue"):
        """Log info message"""
        message = " ".join(str(arg) for arg in args)
        self.console.print(f"[{color}][{title}][/{color}] {message}")
        if self.file_logger:
            self.file_logger.info(f"[{title}] {message}")
    
    def error(self, *args, title: str = "ERROR", color: str = "red"):
        """Log error message"""
        message = " ".join(str(arg) for arg in args)
        self.console.print(f"[{color}][{title}][/{color}] {message}")
        if self.file_logger:
            self.file_logger.error(f"[{title}] {message}")
    
    def warning(self, *args, title: str = "WARNING", color: str = "yellow"):
        """Log warning message"""
        message = " ".join(str(arg) for arg in args)
        self.console.print(f"[{color}][{title}][/{color}] {message}")
        if self.file_logger:
            self.file_logger.warning(f"[{title}] {message}")
    
    def pretty_print_messages(self, message):
        """Pretty print a message - handles both dict and Message objects"""
        # Convert Message object to dict if needed
        if hasattr(message, 'model_dump_json'):
            import json
            message = json.loads(message.model_dump_json())
        elif not isinstance(message, dict):
            # If it's not a dict and not a Message object, try to convert
            message = {"role": "unknown", "content": str(message), "sender": ""}
        
        role = message.get("role", "unknown")
        content = message.get("content")
        sender = message.get("sender", "")
        tool_name = message.get("name", "")
        tool_calls = message.get("tool_calls") or []
        
        # Handle assistant messages with tool calls but no content
        if role == "assistant" and (content is None or content == "") and tool_calls:
            # Show tool calls instead of "No response content"
            tool_call_info = []
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                name = func.get("name", "unknown")
                args = func.get("arguments", "{}")
                try:
                    import json
                    args_dict = json.loads(args)
                    args_str = ", ".join([f"{k}={v}" for k, v in args_dict.items()])
                except:
                    args_str = args[:50] + "..." if len(args) > 50 else args
                tool_call_info.append(f"• {name}({args_str})")
            content = "Making tool calls:\n" + "\n".join(tool_call_info)
        elif content is None:
            # For other cases, show appropriate message
            if tool_calls:
                content = "Executing tools..."
            else:
                content = "No response content"
        else:
            content = str(content)
            # Handle empty results
            if content.strip() in ["{}", "[]", ""]:
                if role == "tool":
                    content = f"Tool {tool_name} executed (no output)"
                else:
                    content = "Task completed (no output)"
        
        # Build title
        if role == "tool":
            title = f"TOOL: {tool_name}" if tool_name else "TOOL"
        elif sender:
            title = f"{sender} ({role})"
        else:
            title = role.upper()
        
        # Truncate long content
        if len(content) > 500:
            content = content[:500] + "... [truncated]"
        
        # Only print if it's an assistant or tool message
        if role in ["assistant", "tool"]:
            border_color = "purple" if role == "tool" else "blue"
            self.console.print(Panel(content, title=title, border_style=border_color))


class LoggerManager:
    """Singleton manager for logger"""
    _logger: Optional[AegisLogger] = None
    
    @classmethod
    def set_logger(cls, logger: AegisLogger):
        """Set the global logger"""
        cls._logger = logger
    
    @classmethod
    def get_logger(cls) -> AegisLogger:
        """Get the global logger, create default if none exists"""
        if cls._logger is None:
            cls._logger = AegisLogger()
        return cls._logger

