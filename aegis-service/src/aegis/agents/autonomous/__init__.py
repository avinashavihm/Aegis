"""
Autonomous Agent Capabilities for Aegis

Provides autonomous operation features including:
- Task planning and decomposition
- Escalation management
- Self-directed execution
"""

from aegis.agents.autonomous.planner import TaskPlanner, PlanExecutor
from aegis.agents.autonomous.escalation_manager import EscalationManager

__all__ = [
    "TaskPlanner",
    "PlanExecutor",
    "EscalationManager"
]

