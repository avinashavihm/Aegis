"""Service for monitoring and metrics collection"""
from sqlmodel import Session, select, func
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from backend.models import (
    WorkflowExecution, AgentExecution, Agent, ExecutionStatus
)


class ExecutionMetrics:
    """Metrics for workflow executions"""
    
    def __init__(
        self,
        total_executions: int = 0,
        successful_executions: int = 0,
        failed_executions: int = 0,
        pending_executions: int = 0,
        running_executions: int = 0,
        average_duration_ms: Optional[float] = None,
        success_rate: float = 0.0,
        queue_depth: int = 0
    ):
        self.total_executions = total_executions
        self.successful_executions = successful_executions
        self.failed_executions = failed_executions
        self.pending_executions = pending_executions
        self.running_executions = running_executions
        self.average_duration_ms = average_duration_ms
        self.success_rate = success_rate
        self.queue_depth = queue_depth
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "pending_executions": self.pending_executions,
            "running_executions": self.running_executions,
            "average_duration_ms": self.average_duration_ms,
            "success_rate": self.success_rate,
            "queue_depth": self.queue_depth
        }


class AgentHealth:
    """Health status for an agent"""
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        status: str,
        last_execution_at: Optional[datetime] = None,
        success_count: int = 0,
        failure_count: int = 0,
        average_response_time_ms: Optional[float] = None,
        uptime_percentage: float = 100.0
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.status = status
        self.last_execution_at = last_execution_at
        self.success_count = success_count
        self.failure_count = failure_count
        self.average_response_time_ms = average_response_time_ms
        self.uptime_percentage = uptime_percentage
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health status to dictionary"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "last_execution_at": self.last_execution_at.isoformat() if self.last_execution_at else None,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "average_response_time_ms": self.average_response_time_ms,
            "uptime_percentage": self.uptime_percentage
        }


def get_execution_metrics(
    session: Session,
    workflow_id: Optional[str] = None,
    time_range_hours: Optional[int] = None
) -> ExecutionMetrics:
    """
    Get execution metrics.
    
    Args:
        session: Database session
        workflow_id: Optional workflow ID to filter by
        time_range_hours: Optional time range in hours
    
    Returns:
        ExecutionMetrics object
    """
    # Build base query
    statement = select(WorkflowExecution)
    
    if workflow_id:
        statement = statement.where(WorkflowExecution.workflow_id == workflow_id)
    
    if time_range_hours:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
        statement = statement.where(WorkflowExecution.created_at >= cutoff_time)
    
    executions = list(session.exec(statement).all())
    
    total = len(executions)
    successful = sum(1 for e in executions if e.status == ExecutionStatus.COMPLETED.value)
    failed = sum(1 for e in executions if e.status == ExecutionStatus.FAILED.value)
    pending = sum(1 for e in executions if e.status == ExecutionStatus.PENDING.value)
    running = sum(1 for e in executions if e.status == ExecutionStatus.RUNNING.value)
    
    # Calculate average duration
    completed_executions = [
        e for e in executions
        if e.status == ExecutionStatus.COMPLETED.value
        and e.started_at
        and e.completed_at
    ]
    
    average_duration_ms = None
    if completed_executions:
        durations = [
            (e.completed_at - e.started_at).total_seconds() * 1000
            for e in completed_executions
        ]
        average_duration_ms = sum(durations) / len(durations)
    
    # Calculate success rate
    success_rate = (successful / total * 100) if total > 0 else 0.0
    
    # Queue depth (pending + running)
    queue_depth = pending + running
    
    return ExecutionMetrics(
        total_executions=total,
        successful_executions=successful,
        failed_executions=failed,
        pending_executions=pending,
        running_executions=running,
        average_duration_ms=average_duration_ms,
        success_rate=success_rate,
        queue_depth=queue_depth
    )


def get_agent_health(
    session: Session,
    agent_id: str
) -> Optional[AgentHealth]:
    """
    Get health status for an agent.
    
    Args:
        session: Database session
        agent_id: Agent ID
    
    Returns:
        AgentHealth object or None if agent not found
    """
    agent = session.get(Agent, agent_id)
    if not agent:
        return None
    
    # Get agent executions
    statement = select(AgentExecution).where(
        AgentExecution.agent_id == agent_id
    ).order_by(AgentExecution.created_at.desc())
    
    agent_executions = list(session.exec(statement).all())
    
    if not agent_executions:
        return AgentHealth(
            agent_id=agent.id,
            agent_name=agent.name,
            status=agent.agent_status
        )
    
    # Calculate metrics
    successful = sum(
        1 for e in agent_executions
        if e.status == ExecutionStatus.COMPLETED.value
    )
    failed = sum(
        1 for e in agent_executions
        if e.status == ExecutionStatus.FAILED.value
    )
    
    # Calculate average response time
    completed_with_duration = [
        e for e in agent_executions
        if e.status == ExecutionStatus.COMPLETED.value
        and e.duration_ms is not None
    ]
    
    average_response_time_ms = None
    if completed_with_duration:
        durations = [e.duration_ms for e in completed_with_duration]
        average_response_time_ms = sum(durations) / len(durations)
    
    # Calculate uptime percentage
    total_executions = len(agent_executions)
    uptime_percentage = (successful / total_executions * 100) if total_executions > 0 else 100.0
    
    # Get last execution time
    last_execution = agent_executions[0] if agent_executions else None
    last_execution_at = last_execution.created_at if last_execution else None
    
    return AgentHealth(
        agent_id=agent.id,
        agent_name=agent.name,
        status=agent.agent_status,
        last_execution_at=last_execution_at,
        success_count=successful,
        failure_count=failed,
        average_response_time_ms=average_response_time_ms,
        uptime_percentage=uptime_percentage
    )


def get_all_agents_health(session: Session) -> List[AgentHealth]:
    """
    Get health status for all agents.
    
    Args:
        session: Database session
    
    Returns:
        List of AgentHealth objects
    """
    statement = select(Agent).where(Agent.deleted_at.is_(None))
    agents = list(session.exec(statement).all())
    
    health_statuses = []
    for agent in agents:
        health = get_agent_health(session, agent.id)
        if health:
            health_statuses.append(health)
    
    return health_statuses


def get_performance_metrics(
    session: Session,
    workflow_id: Optional[str] = None,
    time_range_hours: int = 24
) -> Dict[str, Any]:
    """
    Get performance metrics.
    
    Args:
        session: Database session
        workflow_id: Optional workflow ID to filter by
        time_range_hours: Time range in hours
    
    Returns:
        Dictionary with performance metrics
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
    
    statement = select(WorkflowExecution).where(
        WorkflowExecution.created_at >= cutoff_time
    )
    
    if workflow_id:
        statement = statement.where(WorkflowExecution.workflow_id == workflow_id)
    
    executions = list(session.exec(statement).all())
    
    if not executions:
        return {
            "throughput": 0.0,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "latency_p99_ms": None,
            "error_rate": 0.0
        }
    
    # Calculate throughput (executions per hour)
    time_span_hours = time_range_hours
    throughput = len(executions) / time_span_hours if time_span_hours > 0 else 0.0
    
    # Calculate latencies
    completed_executions = [
        e for e in executions
        if e.status == ExecutionStatus.COMPLETED.value
        and e.started_at
        and e.completed_at
    ]
    
    latencies_ms = []
    if completed_executions:
        latencies_ms = [
            (e.completed_at - e.started_at).total_seconds() * 1000
            for e in completed_executions
        ]
        latencies_ms.sort()
    
    # Calculate percentiles
    def percentile(data: List[float], p: float) -> Optional[float]:
        if not data:
            return None
        k = (len(data) - 1) * p
        f = int(k)
        c = k - f
        if f + 1 < len(data):
            return data[f] + c * (data[f + 1] - data[f])
        return data[f]
    
    latency_p50 = percentile(latencies_ms, 0.50)
    latency_p95 = percentile(latencies_ms, 0.95)
    latency_p99 = percentile(latencies_ms, 0.99)
    
    # Calculate error rate
    failed = sum(1 for e in executions if e.status == ExecutionStatus.FAILED.value)
    error_rate = (failed / len(executions) * 100) if executions else 0.0
    
    return {
        "throughput": throughput,
        "latency_p50_ms": latency_p50,
        "latency_p95_ms": latency_p95,
        "latency_p99_ms": latency_p99,
        "error_rate": error_rate
    }

