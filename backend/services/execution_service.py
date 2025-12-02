from sqlmodel import Session, select
from typing import List, Dict, Set, Optional, Any, Callable
from datetime import datetime
from collections import deque
import asyncio
import concurrent.futures
import time
import random
import math
from backend.models import (
    Workflow, Agent, AgentDependency, WorkflowExecution, AgentExecution,
    ExecutionStatus, ExecutionMode
)
from backend.schemas import (
    ExecutionDetailResponse, WorkflowExecutionResponse, AgentExecutionResponse,
    WorkflowExecutionCreate, ExecutionMode
)
from backend.services import workflow_service
from backend.exceptions import WorkflowNotFoundError, AgentNotFoundError


def topological_sort(agents: List[Agent], dependencies: List[AgentDependency]) -> List[str]:
    """
    Perform topological sort to determine agent execution order.
    Returns list of agent IDs in execution order.
    """
    # Build adjacency list and in-degree count
    graph: Dict[str, List[str]] = {}
    in_degree: Dict[str, int] = {}
    agent_ids: Set[str] = {agent.id for agent in agents}
    
    # Initialize all agents
    for agent in agents:
        graph[agent.id] = []
        in_degree[agent.id] = 0
    
    # Build graph from dependencies
    for dep in dependencies:
        if dep.agent_id in graph and dep.depends_on_agent_id in graph:
            graph[dep.depends_on_agent_id].append(dep.agent_id)
            in_degree[dep.agent_id] = in_degree.get(dep.agent_id, 0) + 1
    
    # Kahn's algorithm for topological sort
    queue = deque()
    result = []
    
    # Add all nodes with in-degree 0
    for agent_id in agent_ids:
        if in_degree.get(agent_id, 0) == 0:
            queue.append(agent_id)
    
    while queue:
        current = queue.popleft()
        result.append(current)
        
        # Reduce in-degree for neighbors
        for neighbor in graph.get(current, []):
            in_degree[neighbor] = in_degree.get(neighbor, 0) - 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Check for cycles (if result length < total agents, there's a cycle)
    if len(result) < len(agent_ids):
        raise ValueError("Dependency graph contains a cycle")
    
    return result


def get_parallel_execution_groups(
    agents: List[Agent],
    dependencies: List[AgentDependency]
) -> List[List[str]]:
    """
    Group agents that can be executed in parallel.
    Returns list of groups, where each group contains agent IDs that can run in parallel.
    """
    # Build dependency graph
    graph: Dict[str, List[str]] = {}
    in_degree: Dict[str, int] = {}
    agent_ids: Set[str] = {agent.id for agent in agents}
    
    # Initialize all agents
    for agent in agents:
        graph[agent.id] = []
        in_degree[agent.id] = 0
    
    # Build graph from dependencies
    for dep in dependencies:
        if dep.agent_id in graph and dep.depends_on_agent_id in graph:
            graph[dep.depends_on_agent_id].append(dep.agent_id)
            in_degree[dep.agent_id] = in_degree.get(dep.agent_id, 0) + 1
    
    groups = []
    remaining = set(agent_ids)
    
    while remaining:
        # Find all agents with no remaining dependencies
        current_group = [
            agent_id for agent_id in remaining
            if in_degree.get(agent_id, 0) == 0
        ]
        
        if not current_group:
            # Cycle detected
            break
        
        groups.append(current_group)
        remaining -= set(current_group)
        
        # Update in-degrees for next iteration
        for agent_id in current_group:
            for neighbor in graph.get(agent_id, []):
                if neighbor in remaining:
                    in_degree[neighbor] = in_degree.get(neighbor, 0) - 1
    
    return groups


def create_workflow_execution(
    session: Session,
    workflow_id: str,
    execution_mode: str = ExecutionMode.SYNC.value,
    execution_context: Optional[Dict[str, Any]] = None,
    priority: int = 0,
    max_retries: int = 3
) -> WorkflowExecution:
    """Create a new workflow execution with execution mode and context"""
    # Verify workflow exists
    workflow_service.get_workflow(session, workflow_id)
    
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        status=ExecutionStatus.PENDING.value,
        execution_mode=execution_mode,
        execution_context=execution_context or {},
        priority=priority,
        max_retries=max_retries
    )
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution


def get_workflow_execution(session: Session, execution_id: str) -> WorkflowExecution:
    """Get workflow execution by ID"""
    execution = session.get(WorkflowExecution, execution_id)
    if not execution:
        raise WorkflowNotFoundError(execution_id)
    return execution


def get_executions(session: Session, workflow_id: Optional[str] = None) -> List[WorkflowExecution]:
    """Get all executions, optionally filtered by workflow_id"""
    statement = select(WorkflowExecution)
    if workflow_id:
        statement = statement.where(WorkflowExecution.workflow_id == workflow_id)
    statement = statement.order_by(WorkflowExecution.created_at.desc())
    return list(session.exec(statement).all())


def evaluate_condition(
    condition: Dict[str, Any],
    execution_context: Dict[str, Any]
) -> bool:
    """
    Evaluate a conditional expression.
    
    Args:
        condition: Condition configuration with 'type', 'field', 'operator', 'value'
        execution_context: Execution context with variables
    
    Returns:
        True if condition is met, False otherwise
    """
    condition_type = condition.get("type", "field")
    operator = condition.get("operator", "equals")
    field = condition.get("field")
    value = condition.get("value")
    
    if condition_type == "field":
        # Get field value from context
        field_value = execution_context.get(field) if field else None
        
        if operator == "equals":
            return field_value == value
        elif operator == "not_equals":
            return field_value != value
        elif operator == "greater_than":
            return field_value > value if field_value is not None else False
        elif operator == "less_than":
            return field_value < value if field_value is not None else False
        elif operator == "contains":
            return value in field_value if isinstance(field_value, (str, list)) else False
        elif operator == "exists":
            return field is not None and field in execution_context
    
    return False


def execute_workflow(
    session: Session,
    workflow_id: str,
    execution_mode: str = ExecutionMode.SYNC.value,
    execution_context: Optional[Dict[str, Any]] = None,
    priority: int = 0,
    max_retries: int = 3
) -> WorkflowExecution:
    """
    Execute a workflow by creating execution records and determining execution order.
    Supports different execution modes: sync, async, parallel.
    This is a simplified version - actual agent execution would be handled by a task queue.
    """
    # Verify workflow exists
    workflow = workflow_service.get_workflow(session, workflow_id)
    
    # Get agents and dependencies
    agents = workflow_service.get_agents(session, workflow_id)
    dependencies = workflow_service.get_dependencies(session, workflow_id)
    
    if not agents:
        raise ValueError("Workflow has no agents to execute")
    
    # Create workflow execution with mode and context
    execution = create_workflow_execution(
        session,
        workflow_id,
        execution_mode=execution_mode,
        execution_context=execution_context or {},
        priority=priority,
        max_retries=max_retries
    )
    
    # Determine execution strategy based on mode
    try:
        if execution_mode == ExecutionMode.PARALLEL.value:
            # Group agents for parallel execution
            execution_groups = get_parallel_execution_groups(agents, dependencies)
            execution.logs = f"Parallel execution with {len(execution_groups)} groups"
        else:
            # Sequential execution (sync, async, etc.)
            execution_order = topological_sort(agents, dependencies)
            execution.logs = f"Sequential execution. Order: {', '.join(execution_order)}"
    except ValueError as e:
        execution.status = ExecutionStatus.FAILED.value
        execution.logs = f"Execution failed: {str(e)}"
        execution.error_details = {"error": str(e), "type": "topological_sort_error"}
        execution.completed_at = datetime.utcnow()
        session.add(execution)
        session.commit()
        return execution
    
    # Create agent execution records
    agent_executions = []
    for agent in agents:
        agent_exec = AgentExecution(
            execution_id=execution.id,
            agent_id=agent.id,
            status=ExecutionStatus.PENDING.value
        )
        session.add(agent_exec)
        agent_executions.append(agent_exec)
    
    # Update execution status
    execution.status = ExecutionStatus.RUNNING.value
    execution.started_at = datetime.utcnow()
    
    session.add(execution)
    session.commit()
    
    # Refresh all records
    session.refresh(execution)
    for agent_exec in agent_executions:
        session.refresh(agent_exec)
    
    return execution


def update_execution_status(
    session: Session,
    execution_id: str,
    status: str,
    logs: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None
) -> WorkflowExecution:
    """Update workflow execution status with error tracking"""
    execution = get_workflow_execution(session, execution_id)
    execution.status = status
    if logs:
        execution.logs = logs
    if error_details:
        execution.error_details = error_details
    if status in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value]:
        execution.completed_at = datetime.utcnow()
    execution.updated_at = datetime.utcnow()
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution


def increment_execution_retry(session: Session, execution_id: str) -> WorkflowExecution:
    """Increment retry count for an execution"""
    execution = get_workflow_execution(session, execution_id)
    execution.retry_count += 1
    execution.updated_at = datetime.utcnow()
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution


def update_agent_execution(
    session: Session,
    agent_execution_id: str,
    status: str,
    output: Optional[str] = None,
    error_message: Optional[str] = None
) -> AgentExecution:
    """Update agent execution status with timing and error tracking"""
    agent_exec = session.get(AgentExecution, agent_execution_id)
    if not agent_exec:
        raise AgentNotFoundError(agent_execution_id)
    
    start_time = agent_exec.started_at or datetime.utcnow()
    
    agent_exec.status = status
    if output:
        agent_exec.output = output
    if error_message:
        agent_exec.error_message = error_message
    
    if status == ExecutionStatus.RUNNING.value and not agent_exec.started_at:
        agent_exec.started_at = datetime.utcnow()
        start_time = agent_exec.started_at
    
    if status in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value]:
        agent_exec.completed_at = datetime.utcnow()
        # Calculate duration in milliseconds
        if agent_exec.started_at:
            duration = (agent_exec.completed_at - agent_exec.started_at).total_seconds() * 1000
            agent_exec.duration_ms = int(duration)
    
    agent_exec.updated_at = datetime.utcnow()
    
    session.add(agent_exec)
    session.commit()
    session.refresh(agent_exec)
    return agent_exec


def get_execution_detail(session: Session, execution_id: str) -> ExecutionDetailResponse:
    """Get detailed execution information with agent executions"""
    execution = get_workflow_execution(session, execution_id)
    
    statement = select(AgentExecution).where(
        AgentExecution.execution_id == execution_id
    ).order_by(AgentExecution.created_at)
    agent_executions = list(session.exec(statement).all())
    
    return ExecutionDetailResponse(
        execution=WorkflowExecutionResponse.model_validate(execution),
        agent_executions=[
            AgentExecutionResponse.model_validate(ae) for ae in agent_executions
        ]
    )


def calculate_retry_delay(
    retry_count: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> float:
    """
    Calculate retry delay with exponential backoff and optional jitter.
    
    Args:
        retry_count: Current retry attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Whether to add random jitter
    
    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (exponential_base ^ retry_count)
    delay = base_delay * (exponential_base ** retry_count)
    
    # Cap at max_delay
    delay = min(delay, max_delay)
    
    # Add jitter (random value between 0 and delay * 0.1)
    if jitter:
        jitter_amount = delay * 0.1 * random.random()
        delay = delay + jitter_amount
    
    return delay


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: Optional[Callable[[Exception], bool]] = None
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Whether to add random jitter
        retry_on: Optional function to determine if exception should be retried
    
    Returns:
        Result of function call
    
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            # Check if we should retry this exception
            if retry_on and not retry_on(e):
                raise
            
            # Don't retry on last attempt
            if attempt < max_retries:
                delay = calculate_retry_delay(
                    attempt,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    exponential_base=exponential_base,
                    jitter=jitter
                )
                time.sleep(delay)
            else:
                # Last attempt failed
                raise
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception

