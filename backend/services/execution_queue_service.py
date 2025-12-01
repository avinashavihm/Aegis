"""Service for managing execution queue with priority"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import heapq
from sqlmodel import Session, select
from backend.models import WorkflowExecution, ExecutionStatus
from backend.services import execution_service


class PriorityQueue:
    """Priority queue for workflow executions"""
    
    def __init__(self):
        self.queue: List[tuple] = []  # (priority, timestamp, execution_id)
        self.execution_map: Dict[str, Dict[str, Any]] = {}
    
    def push(self, execution_id: str, priority: int, execution_data: Dict[str, Any]) -> None:
        """Add execution to queue with priority"""
        timestamp = datetime.utcnow()
        # Use negative priority for max-heap behavior (higher priority = smaller negative number)
        heapq.heappush(self.queue, (-priority, timestamp, execution_id))
        self.execution_map[execution_id] = execution_data
    
    def pop(self) -> Optional[tuple]:
        """Pop highest priority execution"""
        if not self.queue:
            return None
        
        neg_priority, timestamp, execution_id = heapq.heappop(self.queue)
        priority = -neg_priority
        execution_data = self.execution_map.pop(execution_id, {})
        
        return (execution_id, priority, execution_data)
    
    def remove(self, execution_id: str) -> bool:
        """Remove execution from queue"""
        if execution_id not in self.execution_map:
            return False
        
        # Rebuild queue without the removed item
        new_queue = [
            item for item in self.queue
            if item[2] != execution_id
        ]
        heapq.heapify(new_queue)
        self.queue = new_queue
        del self.execution_map[execution_id]
        return True
    
    def size(self) -> int:
        """Get queue size"""
        return len(self.queue)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self.queue) == 0


# Global execution queue
_execution_queue = PriorityQueue()


def get_execution_queue() -> PriorityQueue:
    """Get the global execution queue"""
    return _execution_queue


def cancel_execution(session: Session, execution_id: str) -> bool:
    """Cancel a workflow execution"""
    execution = execution_service.get_workflow_execution(session, execution_id)
    
    if execution.status in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value]:
        return False  # Cannot cancel completed or failed executions
    
    execution.status = ExecutionStatus.CANCELLED.value
    execution.completed_at = datetime.utcnow()
    execution.updated_at = datetime.utcnow()
    session.add(execution)
    session.commit()
    
    # Remove from queue if present
    get_execution_queue().remove(execution_id)
    
    return True


def pause_execution(session: Session, execution_id: str) -> bool:
    """Pause a workflow execution"""
    execution = execution_service.get_workflow_execution(session, execution_id)
    
    if execution.status != ExecutionStatus.RUNNING.value:
        return False  # Can only pause running executions
    
    execution.status = ExecutionStatus.PAUSED.value
    execution.updated_at = datetime.utcnow()
    session.add(execution)
    session.commit()
    
    return True


def resume_execution(session: Session, execution_id: str) -> bool:
    """Resume a paused workflow execution"""
    execution = execution_service.get_workflow_execution(session, execution_id)
    
    if execution.status != ExecutionStatus.PAUSED.value:
        return False  # Can only resume paused executions
    
    execution.status = ExecutionStatus.RUNNING.value
    execution.updated_at = datetime.utcnow()
    session.add(execution)
    session.commit()
    
    return True


def clone_execution(
    session: Session,
    execution_id: str,
    new_workflow_id: Optional[str] = None
) -> WorkflowExecution:
    """Clone an existing execution"""
    original = execution_service.get_workflow_execution(session, execution_id)
    
    workflow_id = new_workflow_id or original.workflow_id
    
    # Create new execution with same configuration
    new_execution = execution_service.create_workflow_execution(
        session,
        workflow_id,
        execution_mode=original.execution_mode,
        execution_context=original.execution_context.copy() if original.execution_context else None,
        priority=original.priority,
        max_retries=original.max_retries
    )
    
    return new_execution

