"""Service for resilience features: circuit breakers, dead letter queue, rollback"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from sqlmodel import Session
from backend.models import WorkflowExecution, AgentExecution, ExecutionStatus
import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.utcnow()
    
    def call(self, func, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed during half-open, go back to open
            self.state = CircuitState.OPEN
            self.success_count = 0
            logger.warning("Circuit breaker OPEN - service still failing")
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.utcnow()
                logger.warning(f"Circuit breaker OPEN - {self.failure_count} failures")


class DeadLetterQueue:
    """Dead letter queue for failed executions"""
    
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
    
    def add_failed_execution(
        self,
        execution_id: str,
        workflow_id: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add failed execution to dead letter queue"""
        entry = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "error": error,
            "error_details": error_details or {},
            "failed_at": datetime.utcnow().isoformat()
        }
        self.queue.append(entry)
        logger.warning(f"Added execution {execution_id} to dead letter queue")
    
    def get_failed_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get failed executions from dead letter queue"""
        results = self.queue
        if workflow_id:
            results = [e for e in results if e.get("workflow_id") == workflow_id]
        return results[:limit]
    
    def remove_execution(self, execution_id: str) -> bool:
        """Remove execution from dead letter queue"""
        original_len = len(self.queue)
        self.queue = [e for e in self.queue if e.get("execution_id") != execution_id]
        return len(self.queue) < original_len


# Global instances
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_dead_letter_queue = DeadLetterQueue()


def get_circuit_breaker(agent_id: str) -> CircuitBreaker:
    """Get or create circuit breaker for an agent"""
    if agent_id not in _circuit_breakers:
        _circuit_breakers[agent_id] = CircuitBreaker()
    return _circuit_breakers[agent_id]


def get_dead_letter_queue() -> DeadLetterQueue:
    """Get the global dead letter queue"""
    return _dead_letter_queue


def rollback_execution(
    session: Session,
    execution_id: str
) -> bool:
    """
    Rollback a failed execution.
    This is a simplified version - actual rollback would depend on workflow logic.
    """
    execution = session.get(WorkflowExecution, execution_id)
    if not execution:
        return False
    
    if execution.status != ExecutionStatus.FAILED.value:
        return False  # Can only rollback failed executions
    
    # Mark as rolled back
    execution.status = ExecutionStatus.CANCELLED.value
    execution.logs = (execution.logs or "") + f"\n[ROLLBACK] Execution rolled back at {datetime.utcnow().isoformat()}"
    execution.updated_at = datetime.utcnow()
    
    # Rollback agent executions
    from sqlmodel import select
    from backend.models import AgentExecution
    
    statement = select(AgentExecution).where(
        AgentExecution.execution_id == execution_id
    )
    agent_executions = list(session.exec(statement).all())
    
    for agent_exec in agent_executions:
        if agent_exec.status == ExecutionStatus.RUNNING.value:
            agent_exec.status = ExecutionStatus.CANCELLED.value
            agent_exec.updated_at = datetime.utcnow()
    
    session.add(execution)
    session.commit()
    
    logger.info(f"Rolled back execution {execution_id}")
    return True

