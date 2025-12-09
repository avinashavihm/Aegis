"""
Aegis CLI Commands

Organized command modules for:
- agent: Agent management (list, create, run, etc.)
- workflow: Workflow management (list, create, run, etc.)
- run: Run management (list, get, cancel, stats)
- tool: Tool management (list, show, custom tools)
- user: User management and authentication
- team: Team management and membership
- role: Role management
- policy: Policy management
- workspace: Workspace management
"""

from src.commands import agent
from src.commands import workflow
from src.commands import run
from src.commands import tool
from src.commands import user
from src.commands import team
from src.commands import role
from src.commands import policy
from src.commands import workspace

__all__ = [
    "agent",
    "workflow", 
    "run",
    "tool",
    "user",
    "team",
    "role",
    "policy",
    "workspace"
]
