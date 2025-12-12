"""
Autonomous Tools for Aegis

Provides tools for autonomous agent operations including:
- Task planning and execution
- Escalation management
"""

from aegis.tools.autonomous.planning_tools import (
    create_task_plan,
    add_subtask,
    set_dependencies,
    get_plan_status,
    execute_next_subtask,
    complete_plan
)
from aegis.tools.autonomous.escalation_tools import (
    check_escalation_needed,
    create_escalation,
    resolve_escalation,
    list_escalations
)

__all__ = [
    "create_task_plan",
    "add_subtask",
    "set_dependencies",
    "get_plan_status",
    "execute_next_subtask",
    "complete_plan",
    "check_escalation_needed",
    "create_escalation",
    "resolve_escalation",
    "list_escalations"
]

