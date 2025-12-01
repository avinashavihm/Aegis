"""Custom exception classes for the application"""
from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class WorkflowNotFoundError(HTTPException):
    """Raised when a workflow is not found"""
    def __init__(self, workflow_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow with id {workflow_id} not found"
        )


class AgentNotFoundError(HTTPException):
    """Raised when an agent is not found"""
    def __init__(self, agent_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id {agent_id} not found"
        )


class DependencyCycleError(HTTPException):
    """Raised when a dependency cycle is detected"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dependency graph contains a cycle. DAG must be acyclic."
        )


class ValidationError(HTTPException):
    """Raised when validation fails"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class TemplateNotFoundError(HTTPException):
    """Raised when a template is not found"""
    def __init__(self, template_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with id {template_id} not found"
        )


class ExecutionError(HTTPException):
    """Raised when execution fails"""
    def __init__(self, detail: str, execution_id: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )
        self.execution_id = execution_id


class RetryExhaustedError(HTTPException):
    """Raised when all retry attempts are exhausted"""
    def __init__(self, detail: str, retry_count: int):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{detail} (retries exhausted after {retry_count} attempts)"
        )
        self.retry_count = retry_count

