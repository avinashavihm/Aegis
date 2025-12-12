"""
Planning Tools for autonomous agents
"""

import json
from typing import List, Optional, Dict, Any

from aegis.registry import register_tool
from aegis.types import TaskStatus
from aegis.agents.autonomous.planner import task_planner, plan_executor


@register_tool("create_task_plan")
def create_task_plan(task_description: str, context_variables: dict = None) -> str:
    """
    Create a new task plan for autonomous execution.
    
    Args:
        task_description: Description of the task to accomplish
        
    Returns:
        JSON string with plan details
    """
    context = context_variables or {}
    plan = task_planner.create_plan(task_description, context)
    
    return json.dumps({
        "status": "success",
        "plan_id": plan.task_id,
        "description": plan.description,
        "message": "Task plan created. Add subtasks using add_subtask tool."
    }, indent=2)


@register_tool("add_subtask")
def add_subtask(plan_id: str, subtask_description: str, 
                depends_on: List[str] = None, context_variables: dict = None) -> str:
    """
    Add a subtask to an existing plan.
    
    Args:
        plan_id: The plan ID to add subtask to
        subtask_description: Description of the subtask
        depends_on: List of subtask IDs this subtask depends on
        
    Returns:
        JSON string with subtask details
    """
    plan = task_planner.get_plan(plan_id)
    if not plan:
        return json.dumps({"status": "error", "message": f"Plan {plan_id} not found"})
    
    # Add the subtask
    task_planner.decompose_task(plan, [subtask_description])
    
    # Get the newly added subtask
    new_subtask = plan.subtasks[-1]
    
    # Add dependencies if specified
    if depends_on:
        task_planner.add_dependency(plan, new_subtask.subtask_id, depends_on)
    
    return json.dumps({
        "status": "success",
        "subtask_id": new_subtask.subtask_id,
        "description": subtask_description,
        "depends_on": depends_on or [],
        "total_subtasks": len(plan.subtasks)
    }, indent=2)


@register_tool("set_dependencies")
def set_dependencies(plan_id: str, subtask_id: str, depends_on: List[str],
                     context_variables: dict = None) -> str:
    """
    Set dependencies for a subtask.
    
    Args:
        plan_id: The plan ID
        subtask_id: The subtask to set dependencies for
        depends_on: List of subtask IDs this subtask depends on
        
    Returns:
        JSON string with dependency details
    """
    plan = task_planner.get_plan(plan_id)
    if not plan:
        return json.dumps({"status": "error", "message": f"Plan {plan_id} not found"})
    
    task_planner.add_dependency(plan, subtask_id, depends_on)
    
    return json.dumps({
        "status": "success",
        "subtask_id": subtask_id,
        "depends_on": depends_on,
        "message": "Dependencies set successfully"
    }, indent=2)


@register_tool("get_plan_status")
def get_plan_status(plan_id: str, context_variables: dict = None) -> str:
    """
    Get the current status of a task plan.
    
    Args:
        plan_id: The plan ID to check
        
    Returns:
        JSON string with plan status details
    """
    plan = task_planner.get_plan(plan_id)
    if not plan:
        return json.dumps({"status": "error", "message": f"Plan {plan_id} not found"})
    
    # Validate the plan
    is_valid, issues = task_planner.validate_plan(plan)
    
    # Get execution order
    execution_order = task_planner.get_execution_order(plan) if is_valid else []
    
    # Get next executable subtasks
    next_subtasks = task_planner.get_next_subtasks(plan)
    
    return json.dumps({
        "status": "success",
        "plan_id": plan.task_id,
        "description": plan.description,
        "overall_status": plan.status.value,
        "is_valid": is_valid,
        "validation_issues": issues,
        "subtasks": [
            {
                "subtask_id": st.subtask_id,
                "description": st.description,
                "status": st.status.value,
                "result": st.result,
                "error": st.error
            }
            for st in plan.subtasks
        ],
        "dependencies": plan.dependencies,
        "execution_order": execution_order,
        "next_executable": [st.subtask_id for st in next_subtasks],
        "completed_count": sum(1 for st in plan.subtasks if st.status == TaskStatus.COMPLETED),
        "total_count": len(plan.subtasks)
    }, indent=2)


@register_tool("execute_next_subtask")
def execute_next_subtask(plan_id: str, subtask_result: str = None,
                         context_variables: dict = None) -> str:
    """
    Mark the next executable subtask and optionally record its result.
    
    Args:
        plan_id: The plan ID
        subtask_result: Optional result to record for the subtask
        
    Returns:
        JSON string with execution status
    """
    plan = task_planner.get_plan(plan_id)
    if not plan:
        return json.dumps({"status": "error", "message": f"Plan {plan_id} not found"})
    
    next_subtasks = task_planner.get_next_subtasks(plan)
    
    if not next_subtasks:
        # Check if all completed
        all_completed = all(st.status == TaskStatus.COMPLETED for st in plan.subtasks)
        if all_completed:
            return json.dumps({
                "status": "success",
                "message": "All subtasks completed",
                "plan_status": plan.status.value
            }, indent=2)
        else:
            return json.dumps({
                "status": "waiting",
                "message": "No subtasks ready for execution (waiting on dependencies)"
            }, indent=2)
    
    # Execute the first available subtask
    subtask = next_subtasks[0]
    subtask.status = TaskStatus.IN_PROGRESS
    
    if subtask_result:
        # Mark as completed with result
        task_planner.update_subtask_status(plan, subtask.subtask_id, 
                                           TaskStatus.COMPLETED, result=subtask_result)
    
    return json.dumps({
        "status": "success",
        "executing": {
            "subtask_id": subtask.subtask_id,
            "description": subtask.description,
            "status": subtask.status.value
        },
        "remaining": len(plan.subtasks) - sum(1 for st in plan.subtasks 
                                               if st.status == TaskStatus.COMPLETED)
    }, indent=2)


@register_tool("complete_subtask")
def complete_subtask(plan_id: str, subtask_id: str, result: str = None,
                     success: bool = True, error: str = None,
                     context_variables: dict = None) -> str:
    """
    Mark a subtask as complete or failed.
    
    Args:
        plan_id: The plan ID
        subtask_id: The subtask ID to complete
        result: The result of the subtask
        success: Whether the subtask succeeded
        error: Error message if failed
        
    Returns:
        JSON string with completion status
    """
    plan = task_planner.get_plan(plan_id)
    if not plan:
        return json.dumps({"status": "error", "message": f"Plan {plan_id} not found"})
    
    status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
    task_planner.update_subtask_status(plan, subtask_id, status, result=result, error=error)
    
    # Get updated plan status
    completed = sum(1 for st in plan.subtasks if st.status == TaskStatus.COMPLETED)
    
    return json.dumps({
        "status": "success",
        "subtask_id": subtask_id,
        "subtask_status": status.value,
        "plan_status": plan.status.value,
        "progress": f"{completed}/{len(plan.subtasks)} subtasks completed"
    }, indent=2)


@register_tool("complete_plan")
def complete_plan(plan_id: str, summary: str = None, context_variables: dict = None) -> str:
    """
    Mark a plan as complete and get final summary.
    
    Args:
        plan_id: The plan ID to complete
        summary: Optional completion summary
        
    Returns:
        JSON string with completion details
    """
    plan = task_planner.get_plan(plan_id)
    if not plan:
        return json.dumps({"status": "error", "message": f"Plan {plan_id} not found"})
    
    # Check if all subtasks are done
    pending = [st for st in plan.subtasks if st.status == TaskStatus.PENDING]
    in_progress = [st for st in plan.subtasks if st.status == TaskStatus.IN_PROGRESS]
    
    if pending or in_progress:
        return json.dumps({
            "status": "warning",
            "message": "Plan has incomplete subtasks",
            "pending": [st.subtask_id for st in pending],
            "in_progress": [st.subtask_id for st in in_progress]
        }, indent=2)
    
    # Compile results
    results = {
        "plan_id": plan.task_id,
        "description": plan.description,
        "status": plan.status.value,
        "summary": summary,
        "subtask_results": [
            {
                "subtask_id": st.subtask_id,
                "description": st.description,
                "status": st.status.value,
                "result": st.result
            }
            for st in plan.subtasks
        ],
        "execution_summary": plan_executor.get_execution_summary()
    }
    
    return json.dumps({
        "status": "success",
        "message": "Plan completed",
        "results": results
    }, indent=2)


@register_tool("list_plans")
def list_plans(status_filter: str = None, context_variables: dict = None) -> str:
    """
    List all task plans.
    
    Args:
        status_filter: Optional filter by status (pending, in_progress, completed, failed)
        
    Returns:
        JSON string with list of plans
    """
    plans = []
    
    for plan_id, plan in task_planner.plans.items():
        if status_filter and plan.status.value != status_filter:
            continue
        
        completed = sum(1 for st in plan.subtasks if st.status == TaskStatus.COMPLETED)
        
        plans.append({
            "plan_id": plan_id,
            "description": plan.description[:100] + "..." if len(plan.description) > 100 else plan.description,
            "status": plan.status.value,
            "progress": f"{completed}/{len(plan.subtasks)}",
            "created_at": plan.created_at
        })
    
    return json.dumps({
        "status": "success",
        "total_plans": len(plans),
        "plans": plans
    }, indent=2)

