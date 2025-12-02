"""Execution router for workflow execution operations"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session
from typing import List, Optional, Dict, Any
from backend.database import get_session
from backend.schemas import (
    WorkflowExecutionResponse, AgentExecutionResponse, ExecutionDetailResponse,
    WorkflowExecutionCreate, ExecutionMode
)
from backend.services import execution_service

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("/workflow/{workflow_id}/execute", response_model=WorkflowExecutionResponse, status_code=201)
def execute_workflow(
    workflow_id: str,
    execution_data: Optional[WorkflowExecutionCreate] = Body(None),
    session: Session = Depends(get_session)
):
    """Execute a workflow with optional execution mode and context"""
    execution_mode = ExecutionMode.SYNC.value
    execution_context = None
    priority = 0
    max_retries = 3
    
    if execution_data:
        execution_mode = execution_data.execution_mode or ExecutionMode.SYNC.value
        execution_context = execution_data.execution_context
        priority = execution_data.priority or 0
        max_retries = execution_data.max_retries or 3
    
    return execution_service.execute_workflow(
        session,
        workflow_id,
        execution_mode=execution_mode,
        execution_context=execution_context,
        priority=priority,
        max_retries=max_retries
    )


@router.get("", response_model=List[WorkflowExecutionResponse])
def get_executions(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    session: Session = Depends(get_session)
):
    """Get all executions, optionally filtered by workflow_id"""
    return execution_service.get_executions(session, workflow_id)


@router.get("/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution(
    execution_id: str,
    session: Session = Depends(get_session)
):
    """Get execution details with agent executions"""
    return execution_service.get_execution_detail(session, execution_id)


@router.post("/{execution_id}/cancel", response_model=WorkflowExecutionResponse)
def cancel_execution(
    execution_id: str,
    session: Session = Depends(get_session)
):
    """Cancel a workflow execution"""
    from backend.services.execution_queue_service import cancel_execution as cancel_exec
    success = cancel_exec(session, execution_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel this execution")
    return execution_service.get_workflow_execution(session, execution_id)


@router.post("/{execution_id}/pause", response_model=WorkflowExecutionResponse)
def pause_execution(
    execution_id: str,
    session: Session = Depends(get_session)
):
    """Pause a workflow execution"""
    from backend.services.execution_queue_service import pause_execution as pause_exec
    success = pause_exec(session, execution_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause this execution")
    return execution_service.get_workflow_execution(session, execution_id)


@router.post("/{execution_id}/resume", response_model=WorkflowExecutionResponse)
def resume_execution(
    execution_id: str,
    session: Session = Depends(get_session)
):
    """Resume a paused workflow execution"""
    from backend.services.execution_queue_service import resume_execution as resume_exec
    success = resume_exec(session, execution_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume this execution")
    return execution_service.get_workflow_execution(session, execution_id)


@router.post("/{execution_id}/clone", response_model=WorkflowExecutionResponse, status_code=201)
def clone_execution(
    execution_id: str,
    new_workflow_id: Optional[str] = Body(None),
    session: Session = Depends(get_session)
):
    """Clone an existing execution"""
    from backend.services.execution_queue_service import clone_execution as clone_exec
    return clone_exec(session, execution_id, new_workflow_id)

