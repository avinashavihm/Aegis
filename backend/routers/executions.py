"""Execution router for workflow execution operations"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List, Optional
from backend.database import get_session
from backend.schemas import (
    WorkflowExecutionResponse, AgentExecutionResponse, ExecutionDetailResponse
)
from backend.services import execution_service

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("/workflow/{workflow_id}/execute", response_model=WorkflowExecutionResponse, status_code=201)
def execute_workflow(
    workflow_id: str,
    session: Session = Depends(get_session)
):
    """Execute a workflow"""
    return execution_service.execute_workflow(session, workflow_id)


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

