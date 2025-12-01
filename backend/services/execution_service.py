from sqlmodel import Session, select
from typing import List, Dict, Set, Optional
from datetime import datetime
from collections import deque
from backend.models import (
    Workflow, Agent, AgentDependency, WorkflowExecution, AgentExecution,
    ExecutionStatus
)
from backend.schemas import ExecutionDetailResponse, WorkflowExecutionResponse, AgentExecutionResponse
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


def create_workflow_execution(session: Session, workflow_id: str) -> WorkflowExecution:
    """Create a new workflow execution"""
    # Verify workflow exists
    workflow_service.get_workflow(session, workflow_id)
    
    execution = WorkflowExecution(
        workflow_id=workflow_id,
        status=ExecutionStatus.PENDING.value
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


def execute_workflow(session: Session, workflow_id: str) -> WorkflowExecution:
    """
    Execute a workflow by creating execution records and determining execution order.
    This is a simplified version - actual agent execution would be handled by a task queue.
    """
    # Verify workflow exists
    workflow = workflow_service.get_workflow(session, workflow_id)
    
    # Get agents and dependencies
    agents = workflow_service.get_agents(session, workflow_id)
    dependencies = workflow_service.get_dependencies(session, workflow_id)
    
    if not agents:
        raise ValueError("Workflow has no agents to execute")
    
    # Create workflow execution
    execution = create_workflow_execution(session, workflow_id)
    
    # Determine execution order using topological sort
    try:
        execution_order = topological_sort(agents, dependencies)
    except ValueError as e:
        execution.status = ExecutionStatus.FAILED.value
        execution.logs = f"Execution failed: {str(e)}"
        execution.completed_at = datetime.utcnow()
        session.add(execution)
        session.commit()
        return execution
    
    # Create agent execution records
    agent_executions = []
    for agent_id in execution_order:
        agent_exec = AgentExecution(
            execution_id=execution.id,
            agent_id=agent_id,
            status=ExecutionStatus.PENDING.value
        )
        session.add(agent_exec)
        agent_executions.append(agent_exec)
    
    # Update execution status
    execution.status = ExecutionStatus.RUNNING.value
    execution.started_at = datetime.utcnow()
    execution.logs = f"Execution started. Order: {', '.join(execution_order)}"
    
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
    logs: Optional[str] = None
) -> WorkflowExecution:
    """Update workflow execution status"""
    execution = get_workflow_execution(session, execution_id)
    execution.status = status
    if logs:
        execution.logs = logs
    if status in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value]:
        execution.completed_at = datetime.utcnow()
    execution.updated_at = datetime.utcnow()
    session.add(execution)
    session.commit()
    session.refresh(execution)
    return execution


def update_agent_execution(
    session: Session,
    agent_execution_id: str,
    status: str,
    output: Optional[str] = None
) -> AgentExecution:
    """Update agent execution status"""
    agent_exec = session.get(AgentExecution, agent_execution_id)
    if not agent_exec:
        raise AgentNotFoundError(agent_execution_id)
    
    agent_exec.status = status
    if output:
        agent_exec.output = output
    if status == ExecutionStatus.RUNNING.value and not agent_exec.started_at:
        agent_exec.started_at = datetime.utcnow()
    if status in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value]:
        agent_exec.completed_at = datetime.utcnow()
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

