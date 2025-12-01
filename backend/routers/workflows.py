from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlmodel import Session
from typing import List, Optional
from backend.database import get_session
from backend.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    AgentResponse, AgentCreate,
    DependencyResponse, DependencyCreate,
    AgentsUpdateRequest, DependenciesUpdateRequest,
    WorkflowListResponse
)
from backend.services import workflow_service, export_service

router = APIRouter(prefix="/workflow", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=201)
def create_workflow(
    workflow_data: WorkflowCreate,
    session: Session = Depends(get_session)
):
    """Create a new workflow"""
    workflow = workflow_service.create_workflow(session, workflow_data)
    return workflow


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    session: Session = Depends(get_session)
):
    """Get workflow by ID"""
    return workflow_service.get_workflow(session, workflow_id)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    session: Session = Depends(get_session)
):
    """Update a workflow"""
    return workflow_service.update_workflow(session, workflow_id, workflow_data)


@router.delete("/{workflow_id}", status_code=204)
def delete_workflow(
    workflow_id: str,
    session: Session = Depends(get_session)
):
    """Delete a workflow (soft delete)"""
    workflow_service.delete_workflow(session, workflow_id)
    return None


@router.get("", response_model=WorkflowListResponse)
def get_workflows(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query(None, description="Sort by: name, created_at, updated_at"),
    session: Session = Depends(get_session)
):
    """Get all workflows with pagination, search, and sorting"""
    return workflow_service.get_workflows_paginated(
        session, page=page, limit=limit, search=search, sort=sort
    )


@router.get("/{workflow_id}/agents", response_model=List[AgentResponse])
def get_agents(
    workflow_id: str,
    session: Session = Depends(get_session)
):
    """Get all agents for a workflow"""
    return workflow_service.get_agents(session, workflow_id)


@router.put("/{workflow_id}/agents", response_model=List[AgentResponse])
def update_agents(
    workflow_id: str,
    agents_request: AgentsUpdateRequest,
    session: Session = Depends(get_session)
):
    """Update agents for a workflow (replaces all existing agents)"""
    return workflow_service.update_agents(session, workflow_id, agents_request.agents)


@router.get("/{workflow_id}/dependencies", response_model=List[DependencyResponse])
def get_dependencies(
    workflow_id: str,
    session: Session = Depends(get_session)
):
    """Get all dependencies for a workflow"""
    return workflow_service.get_dependencies(session, workflow_id)


@router.put("/{workflow_id}/dependencies", response_model=List[DependencyResponse])
def update_dependencies(
    workflow_id: str,
    dependencies_request: DependenciesUpdateRequest,
    session: Session = Depends(get_session)
):
    """Update dependencies for a workflow with cycle validation"""
    return workflow_service.update_dependencies(
        session, workflow_id, dependencies_request.dependencies
    )


@router.get("/{workflow_id}/export")
def export_workflow(
    workflow_id: str,
    format: str = Query("json", regex="^(json|yaml)$"),
    session: Session = Depends(get_session)
):
    """Export workflow to JSON or YAML"""
    if format == "json":
        content = export_service.export_workflow_to_json(session, workflow_id)
        media_type = "application/json"
        filename = f"workflow_{workflow_id}.json"
    else:
        content = export_service.export_workflow_to_yaml(session, workflow_id)
        media_type = "application/x-yaml"
        filename = f"workflow_{workflow_id}.yaml"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/import", response_model=WorkflowResponse, status_code=201)
async def import_workflow(
    request: Request,
    format: str = Query("json", regex="^(json|yaml)$"),
    workflow_name: Optional[str] = Query(None),
    workflow_description: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    """Import workflow from JSON or YAML"""
    body = await request.body()
    content = body.decode("utf-8")
    
    if format == "json":
        workflow = export_service.import_workflow_from_json(
            session, content,
            workflow_name=workflow_name,
            workflow_description=workflow_description
        )
    else:
        workflow = export_service.import_workflow_from_yaml(
            session, content,
            workflow_name=workflow_name,
            workflow_description=workflow_description
        )
    
    return workflow

