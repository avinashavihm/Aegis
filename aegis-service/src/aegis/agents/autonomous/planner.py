"""
Task Planning System for autonomous agents

Provides task decomposition, dependency management, and plan execution.
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

from aegis.types import TaskPlan, SubTask, TaskStatus, Agent
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


@dataclass
class PlanStep:
    """A single step in an execution plan"""
    step_id: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskPlanner:
    """
    Plans and decomposes tasks into executable steps.
    Supports dependency management and plan optimization.
    """
    
    def __init__(self):
        self.plans: Dict[str, TaskPlan] = {}
        self.step_registry: Dict[str, PlanStep] = {}
    
    def create_plan(self, task_description: str, context: Dict[str, Any] = None) -> TaskPlan:
        """
        Create a new task plan from a description.
        
        Args:
            task_description: Description of the task to plan
            context: Additional context for planning
            
        Returns:
            TaskPlan object
        """
        plan_id = str(uuid.uuid4())[:8]
        
        plan = TaskPlan(
            task_id=plan_id,
            description=task_description,
            subtasks=[],
            dependencies={},
            status=TaskStatus.PENDING,
            metadata=context or {}
        )
        
        self.plans[plan_id] = plan
        logger.info(f"Created task plan: {plan_id}", title="Planner")
        
        return plan
    
    def decompose_task(self, plan: TaskPlan, subtask_descriptions: List[str]) -> TaskPlan:
        """
        Decompose a task into subtasks.
        
        Args:
            plan: The task plan to decompose
            subtask_descriptions: List of subtask descriptions
            
        Returns:
            Updated TaskPlan
        """
        for i, description in enumerate(subtask_descriptions):
            subtask = SubTask(
                subtask_id=f"{plan.task_id}-{i+1}",
                parent_task_id=plan.task_id,
                description=description,
                status=TaskStatus.PENDING
            )
            plan.subtasks.append(subtask)
        
        return plan
    
    def add_dependency(self, plan: TaskPlan, subtask_id: str, depends_on: List[str]) -> TaskPlan:
        """
        Add dependencies between subtasks.
        
        Args:
            plan: The task plan
            subtask_id: The subtask that has dependencies
            depends_on: List of subtask IDs this subtask depends on
            
        Returns:
            Updated TaskPlan
        """
        plan.dependencies[subtask_id] = depends_on
        return plan
    
    def get_execution_order(self, plan: TaskPlan) -> List[List[str]]:
        """
        Get the execution order of subtasks respecting dependencies.
        Returns batches of subtasks that can be executed in parallel.
        
        Args:
            plan: The task plan
            
        Returns:
            List of batches, each batch contains subtask IDs that can run in parallel
        """
        # Build dependency graph
        all_subtasks = {st.subtask_id for st in plan.subtasks}
        dependencies = plan.dependencies.copy()
        
        # Initialize with subtasks that have no dependencies
        for subtask in plan.subtasks:
            if subtask.subtask_id not in dependencies:
                dependencies[subtask.subtask_id] = []
        
        batches = []
        completed = set()
        
        while len(completed) < len(all_subtasks):
            # Find subtasks whose dependencies are all completed
            batch = []
            for subtask_id in all_subtasks - completed:
                deps = dependencies.get(subtask_id, [])
                if all(dep in completed for dep in deps):
                    batch.append(subtask_id)
            
            if not batch:
                # Circular dependency or error
                remaining = all_subtasks - completed
                logger.warning(f"Could not resolve execution order for: {remaining}", title="Planner")
                batch = list(remaining)  # Force remaining
            
            batches.append(batch)
            completed.update(batch)
        
        return batches
    
    def optimize_plan(self, plan: TaskPlan) -> TaskPlan:
        """
        Optimize the execution plan for efficiency.
        
        Args:
            plan: The task plan to optimize
            
        Returns:
            Optimized TaskPlan
        """
        # Group similar subtasks
        # Reorder for minimal context switching
        # Identify parallelizable steps
        
        execution_order = self.get_execution_order(plan)
        
        # Update metadata with optimization info
        plan.metadata["execution_order"] = execution_order
        plan.metadata["parallel_batches"] = len(execution_order)
        plan.metadata["optimized_at"] = datetime.now().isoformat()
        
        return plan
    
    def validate_plan(self, plan: TaskPlan) -> tuple[bool, List[str]]:
        """
        Validate a task plan for completeness and consistency.
        
        Args:
            plan: The task plan to validate
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        if not plan.description:
            issues.append("Plan has no description")
        
        if not plan.subtasks:
            issues.append("Plan has no subtasks")
        
        # Check for circular dependencies
        try:
            self.get_execution_order(plan)
        except Exception as e:
            issues.append(f"Dependency resolution error: {str(e)}")
        
        # Check for undefined dependencies
        subtask_ids = {st.subtask_id for st in plan.subtasks}
        for subtask_id, deps in plan.dependencies.items():
            for dep in deps:
                if dep not in subtask_ids:
                    issues.append(f"Subtask {subtask_id} depends on undefined subtask {dep}")
        
        return len(issues) == 0, issues
    
    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Get a plan by ID"""
        return self.plans.get(plan_id)
    
    def update_subtask_status(self, plan: TaskPlan, subtask_id: str, 
                               status: TaskStatus, result: str = None, error: str = None) -> TaskPlan:
        """
        Update the status of a subtask.
        
        Args:
            plan: The task plan
            subtask_id: The subtask ID
            status: New status
            result: Result if completed
            error: Error if failed
            
        Returns:
            Updated TaskPlan
        """
        for subtask in plan.subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = status
                if result:
                    subtask.result = result
                if error:
                    subtask.error = error
                break
        
        # Update overall plan status
        self._update_plan_status(plan)
        
        return plan
    
    def _update_plan_status(self, plan: TaskPlan):
        """Update the overall plan status based on subtask statuses"""
        if not plan.subtasks:
            return
        
        statuses = [st.status for st in plan.subtasks]
        
        if all(s == TaskStatus.COMPLETED for s in statuses):
            plan.status = TaskStatus.COMPLETED
            plan.completed_at = datetime.now().isoformat()
        elif any(s == TaskStatus.FAILED for s in statuses):
            plan.status = TaskStatus.FAILED
        elif any(s == TaskStatus.IN_PROGRESS for s in statuses):
            plan.status = TaskStatus.IN_PROGRESS
        elif any(s == TaskStatus.ESCALATED for s in statuses):
            plan.status = TaskStatus.ESCALATED
    
    def get_next_subtasks(self, plan: TaskPlan) -> List[SubTask]:
        """
        Get the next subtasks that can be executed.
        
        Args:
            plan: The task plan
            
        Returns:
            List of executable subtasks
        """
        completed = {st.subtask_id for st in plan.subtasks 
                     if st.status == TaskStatus.COMPLETED}
        
        executable = []
        for subtask in plan.subtasks:
            if subtask.status != TaskStatus.PENDING:
                continue
            
            deps = plan.dependencies.get(subtask.subtask_id, [])
            if all(dep in completed for dep in deps):
                executable.append(subtask)
        
        return executable
    
    def to_dict(self, plan: TaskPlan) -> Dict[str, Any]:
        """Convert plan to dictionary for serialization"""
        return {
            "task_id": plan.task_id,
            "description": plan.description,
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
            "status": plan.status.value,
            "created_at": plan.created_at,
            "completed_at": plan.completed_at,
            "metadata": plan.metadata
        }


class PlanExecutor:
    """
    Executes task plans with monitoring and error handling.
    """
    
    def __init__(self, planner: TaskPlanner = None):
        self.planner = planner or TaskPlanner()
        self.execution_history: List[Dict[str, Any]] = []
        self.callbacks: Dict[str, Callable] = {}
    
    def register_callback(self, event: str, callback: Callable):
        """
        Register a callback for execution events.
        
        Args:
            event: Event name (on_start, on_complete, on_error, on_subtask_complete)
            callback: Callback function
        """
        self.callbacks[event] = callback
    
    def _trigger_callback(self, event: str, **kwargs):
        """Trigger a registered callback"""
        if event in self.callbacks:
            try:
                self.callbacks[event](**kwargs)
            except Exception as e:
                logger.warning(f"Callback error for {event}: {e}", title="PlanExecutor")
    
    def execute_plan(self, plan: TaskPlan, executor: Callable[[SubTask], str]) -> Dict[str, Any]:
        """
        Execute a task plan.
        
        Args:
            plan: The task plan to execute
            executor: Function to execute each subtask
            
        Returns:
            Execution results
        """
        self._trigger_callback("on_start", plan=plan)
        plan.status = TaskStatus.IN_PROGRESS
        
        results = {
            "plan_id": plan.task_id,
            "subtask_results": {},
            "success": True,
            "errors": []
        }
        
        # Execute in dependency order
        execution_order = self.planner.get_execution_order(plan)
        
        for batch in execution_order:
            batch_results = self._execute_batch(plan, batch, executor)
            results["subtask_results"].update(batch_results)
            
            # Check for failures
            for subtask_id, result in batch_results.items():
                if result.get("status") == TaskStatus.FAILED:
                    results["success"] = False
                    results["errors"].append({
                        "subtask_id": subtask_id,
                        "error": result.get("error")
                    })
        
        # Update plan status
        self.planner._update_plan_status(plan)
        
        self._trigger_callback("on_complete", plan=plan, results=results)
        
        # Record execution
        self.execution_history.append({
            "plan_id": plan.task_id,
            "completed_at": datetime.now().isoformat(),
            "success": results["success"],
            "subtask_count": len(plan.subtasks)
        })
        
        return results
    
    def _execute_batch(self, plan: TaskPlan, batch: List[str], 
                       executor: Callable[[SubTask], str]) -> Dict[str, Any]:
        """Execute a batch of subtasks"""
        results = {}
        
        for subtask_id in batch:
            subtask = next((st for st in plan.subtasks if st.subtask_id == subtask_id), None)
            if not subtask:
                continue
            
            subtask.status = TaskStatus.IN_PROGRESS
            
            try:
                result = executor(subtask)
                subtask.status = TaskStatus.COMPLETED
                subtask.result = result
                
                results[subtask_id] = {
                    "status": TaskStatus.COMPLETED,
                    "result": result
                }
                
                self._trigger_callback("on_subtask_complete", subtask=subtask, result=result)
                
            except Exception as e:
                subtask.status = TaskStatus.FAILED
                subtask.error = str(e)
                subtask.retry_count += 1
                
                results[subtask_id] = {
                    "status": TaskStatus.FAILED,
                    "error": str(e)
                }
                
                self._trigger_callback("on_error", subtask=subtask, error=e)
                
                # Attempt retry if within limits
                if subtask.retry_count < subtask.max_retries:
                    logger.info(f"Retrying subtask {subtask_id} (attempt {subtask.retry_count})", 
                               title="PlanExecutor")
                    subtask.status = TaskStatus.PENDING
        
        return results
    
    async def execute_plan_async(self, plan: TaskPlan, 
                                  executor: Callable[[SubTask], str]) -> Dict[str, Any]:
        """
        Execute a task plan asynchronously with parallel batch execution.
        
        Args:
            plan: The task plan to execute
            executor: Async function to execute each subtask
            
        Returns:
            Execution results
        """
        import asyncio
        
        self._trigger_callback("on_start", plan=plan)
        plan.status = TaskStatus.IN_PROGRESS
        
        results = {
            "plan_id": plan.task_id,
            "subtask_results": {},
            "success": True,
            "errors": []
        }
        
        execution_order = self.planner.get_execution_order(plan)
        
        for batch in execution_order:
            # Execute batch in parallel
            tasks = []
            for subtask_id in batch:
                subtask = next((st for st in plan.subtasks if st.subtask_id == subtask_id), None)
                if subtask:
                    tasks.append(self._execute_subtask_async(subtask, executor))
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for subtask_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results["subtask_results"][subtask_id] = {
                        "status": TaskStatus.FAILED,
                        "error": str(result)
                    }
                    results["success"] = False
                    results["errors"].append({"subtask_id": subtask_id, "error": str(result)})
                else:
                    results["subtask_results"][subtask_id] = result
        
        self.planner._update_plan_status(plan)
        self._trigger_callback("on_complete", plan=plan, results=results)
        
        return results
    
    async def _execute_subtask_async(self, subtask: SubTask, 
                                      executor: Callable) -> Dict[str, Any]:
        """Execute a single subtask asynchronously"""
        import asyncio
        
        subtask.status = TaskStatus.IN_PROGRESS
        
        try:
            if asyncio.iscoroutinefunction(executor):
                result = await executor(subtask)
            else:
                result = executor(subtask)
            
            subtask.status = TaskStatus.COMPLETED
            subtask.result = result
            
            return {"status": TaskStatus.COMPLETED, "result": result}
            
        except Exception as e:
            subtask.status = TaskStatus.FAILED
            subtask.error = str(e)
            return {"status": TaskStatus.FAILED, "error": str(e)}
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of execution history"""
        if not self.execution_history:
            return {"total_executions": 0}
        
        successful = sum(1 for e in self.execution_history if e["success"])
        
        return {
            "total_executions": len(self.execution_history),
            "successful": successful,
            "failed": len(self.execution_history) - successful,
            "success_rate": successful / len(self.execution_history) if self.execution_history else 0,
            "recent_executions": self.execution_history[-5:]
        }


# Global planner instance
task_planner = TaskPlanner()
plan_executor = PlanExecutor(task_planner)

