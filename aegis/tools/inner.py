"""
Internal tools for case resolution and task management
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from aegis.types import Result, TaskStatus


class TaskTracker:
    """
    Tracks task status, progress, and verification.
    """
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    _progress_callbacks: List[callable] = []
    
    @classmethod
    def start_task(cls, task_id: str, description: str, total_steps: int = 1) -> str:
        """Start tracking a task"""
        cls._tasks[task_id] = {
            "task_id": task_id,
            "description": description,
            "status": TaskStatus.IN_PROGRESS.value,
            "total_steps": total_steps,
            "completed_steps": 0,
            "progress_percent": 0,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "steps": [],
            "verification": None,
            "result": None,
            "error": None
        }
        cls._notify_progress(task_id)
        return task_id
    
    @classmethod
    def update_progress(cls, task_id: str, step_name: str, 
                        step_result: str = None, increment: bool = True):
        """Update task progress"""
        if task_id not in cls._tasks:
            return
        
        task = cls._tasks[task_id]
        
        step_info = {
            "step_name": step_name,
            "result": step_result,
            "completed_at": datetime.now().isoformat()
        }
        task["steps"].append(step_info)
        
        if increment:
            task["completed_steps"] += 1
            task["progress_percent"] = int(
                (task["completed_steps"] / task["total_steps"]) * 100
            )
        
        cls._notify_progress(task_id)
    
    @classmethod
    def complete_task(cls, task_id: str, result: str, 
                      verification: Dict[str, Any] = None):
        """Mark a task as complete"""
        if task_id not in cls._tasks:
            return
        
        task = cls._tasks[task_id]
        task["status"] = TaskStatus.COMPLETED.value
        task["completed_at"] = datetime.now().isoformat()
        task["result"] = result
        task["progress_percent"] = 100
        task["verification"] = verification
        
        cls._notify_progress(task_id)
    
    @classmethod
    def fail_task(cls, task_id: str, error: str):
        """Mark a task as failed"""
        if task_id not in cls._tasks:
            return
        
        task = cls._tasks[task_id]
        task["status"] = TaskStatus.FAILED.value
        task["error"] = error
        task["completed_at"] = datetime.now().isoformat()
        
        cls._notify_progress(task_id)
    
    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information"""
        return cls._tasks.get(task_id)
    
    @classmethod
    def get_progress(cls, task_id: str) -> Dict[str, Any]:
        """Get task progress"""
        if task_id not in cls._tasks:
            return {"error": "Task not found"}
        
        task = cls._tasks[task_id]
        return {
            "task_id": task_id,
            "status": task["status"],
            "progress_percent": task["progress_percent"],
            "completed_steps": task["completed_steps"],
            "total_steps": task["total_steps"],
            "steps_completed": [s["step_name"] for s in task["steps"]]
        }
    
    @classmethod
    def register_progress_callback(cls, callback: callable):
        """Register a callback for progress updates"""
        cls._progress_callbacks.append(callback)
    
    @classmethod
    def _notify_progress(cls, task_id: str):
        """Notify registered callbacks of progress"""
        task = cls._tasks.get(task_id)
        if task:
            for callback in cls._progress_callbacks:
                try:
                    callback(task)
                except:
                    pass
    
    @classmethod
    def list_tasks(cls, status: str = None) -> List[Dict[str, Any]]:
        """List all tasks, optionally filtered by status"""
        tasks = list(cls._tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks
    
    @classmethod
    def cleanup_old_tasks(cls, max_tasks: int = 100):
        """Keep only the most recent tasks"""
        if len(cls._tasks) <= max_tasks:
            return
        
        sorted_tasks = sorted(
            cls._tasks.items(),
            key=lambda x: x[1]["started_at"],
            reverse=True
        )
        
        cls._tasks = dict(sorted_tasks[:max_tasks])


# Global task tracker
task_tracker = TaskTracker()


def case_resolved(result: str, context_variables: dict = None) -> str:
    """
    Use this tool to indicate that the case is resolved. You can use this tool only after you truly resolve the case with existing tools and created new tools.
    Please encapsulate your final answer (answer ONLY) within <solution> and </solution>.
    
    Args:
        result: The final result of the case resolution following the instructions.
        
    Example: case_resolved(`The answer to the question is <solution> 42 </solution>`)
    """
    # Track completion if there's an active task
    context = context_variables or {}
    task_id = context.get("current_task_id")
    
    if task_id:
        verification = {
            "verified_at": datetime.now().isoformat(),
            "verification_method": "auto",
            "verified_by": context.get("current_agent", "unknown")
        }
        task_tracker.complete_task(task_id, result, verification)
    
    return f"Case resolved. No further actions are needed. The result of the case resolution is: {result}"


def case_not_resolved(failure_reason: str, take_away_message: str, context_variables: dict = None) -> str:
    """
    Use this tool to indicate that the case is not resolved when all agents have tried their best.
    [IMPORTANT] Please do not use this function unless all of you have tried your best.
    You should give the failure reason to tell the user why the case is not resolved, and give the take away message to tell which information you gain from creating new tools.
    
    Args:
        failure_reason: The reason why the case is not resolved.
        take_away_message: The message to take away from the case.
    """
    context = context_variables or {}
    task_id = context.get("current_task_id")
    
    if task_id:
        task_tracker.fail_task(task_id, failure_reason)
    
    return f"Case not resolved. The reason is: {failure_reason}. But though creating new tools, I gain some information: {take_away_message}"


def report_progress(step_name: str, step_result: str = None, 
                    context_variables: dict = None) -> str:
    """
    Report progress on the current task.
    
    Args:
        step_name: Name of the completed step
        step_result: Optional result of the step
        
    Returns:
        Progress status message
    """
    context = context_variables or {}
    task_id = context.get("current_task_id")
    
    if task_id:
        task_tracker.update_progress(task_id, step_name, step_result)
        progress = task_tracker.get_progress(task_id)
        return json.dumps({
            "status": "progress_reported",
            "step": step_name,
            "progress": progress
        }, indent=2)
    
    return json.dumps({
        "status": "no_active_task",
        "message": "Progress reported but no task tracking active"
    }, indent=2)


def get_task_status(task_id: str = None, context_variables: dict = None) -> str:
    """
    Get the status of a task.
    
    Args:
        task_id: Optional task ID (uses current task if not provided)
        
    Returns:
        Task status information
    """
    context = context_variables or {}
    
    if not task_id:
        task_id = context.get("current_task_id")
    
    if not task_id:
        # Return all recent tasks
        tasks = task_tracker.list_tasks()
        return json.dumps({
            "status": "success",
            "tasks": tasks[-10:]  # Last 10 tasks
        }, indent=2)
    
    task = task_tracker.get_task(task_id)
    if task:
        return json.dumps({
            "status": "success",
            "task": task
        }, indent=2)
    
    return json.dumps({
        "status": "error",
        "message": f"Task {task_id} not found"
    }, indent=2)


def verify_result(result: str, verification_criteria: str, 
                  context_variables: dict = None) -> str:
    """
    Verify a result against criteria before marking as complete.
    
    Args:
        result: The result to verify
        verification_criteria: Criteria to check against
        
    Returns:
        Verification status
    """
    context = context_variables or {}
    
    # Simple verification - check if result is not empty and contains key elements
    verification = {
        "verified_at": datetime.now().isoformat(),
        "criteria": verification_criteria,
        "passed": True,
        "checks": []
    }
    
    # Check result is not empty
    if not result or not result.strip():
        verification["passed"] = False
        verification["checks"].append({
            "check": "not_empty",
            "passed": False,
            "message": "Result is empty"
        })
    else:
        verification["checks"].append({
            "check": "not_empty",
            "passed": True
        })
    
    # Check for error indicators
    error_keywords = ["error", "failed", "exception", "not found"]
    has_error = any(kw in result.lower() for kw in error_keywords)
    
    verification["checks"].append({
        "check": "no_errors",
        "passed": not has_error,
        "message": "Result contains error indicators" if has_error else None
    })
    
    if has_error:
        verification["passed"] = False
    
    return json.dumps({
        "status": "success",
        "verification": verification
    }, indent=2)


def rollback_task(task_id: str = None, reason: str = "", 
                  context_variables: dict = None) -> str:
    """
    Mark a task for rollback due to issues.
    
    Args:
        task_id: Task to rollback (uses current if not provided)
        reason: Reason for rollback
        
    Returns:
        Rollback status
    """
    context = context_variables or {}
    
    if not task_id:
        task_id = context.get("current_task_id")
    
    if not task_id:
        return json.dumps({
            "status": "error",
            "message": "No task ID provided and no active task"
        }, indent=2)
    
    task = task_tracker.get_task(task_id)
    if not task:
        return json.dumps({
            "status": "error",
            "message": f"Task {task_id} not found"
        }, indent=2)
    
    # Mark task as needing rollback
    task_tracker._tasks[task_id]["status"] = "rollback_requested"
    task_tracker._tasks[task_id]["rollback_reason"] = reason
    task_tracker._tasks[task_id]["rollback_at"] = datetime.now().isoformat()
    
    return json.dumps({
        "status": "success",
        "task_id": task_id,
        "message": f"Task marked for rollback: {reason}",
        "steps_to_undo": [s["step_name"] for s in task.get("steps", [])]
    }, indent=2)


def set_task_dependency(task_id: str, depends_on: List[str], 
                        context_variables: dict = None) -> str:
    """
    Set dependencies for a task.
    
    Args:
        task_id: Task ID
        depends_on: List of task IDs this task depends on
        
    Returns:
        Dependency status
    """
    task = task_tracker.get_task(task_id)
    if not task:
        return json.dumps({
            "status": "error",
            "message": f"Task {task_id} not found"
        }, indent=2)
    
    # Verify all dependencies exist
    missing = [t for t in depends_on if not task_tracker.get_task(t)]
    if missing:
        return json.dumps({
            "status": "error",
            "message": f"Dependency tasks not found: {missing}"
        }, indent=2)
    
    task_tracker._tasks[task_id]["dependencies"] = depends_on
    
    # Check if dependencies are complete
    all_complete = all(
        task_tracker.get_task(t)["status"] == TaskStatus.COMPLETED.value
        for t in depends_on
    )
    
    return json.dumps({
        "status": "success",
        "task_id": task_id,
        "dependencies": depends_on,
        "dependencies_complete": all_complete
    }, indent=2)
