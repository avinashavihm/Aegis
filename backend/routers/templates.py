"""Template router for workflow template operations"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from backend.database import get_session
from backend.schemas import (
    WorkflowTemplateCreate, WorkflowTemplateUpdate, WorkflowTemplateResponse,
    TemplateApplyRequest, WorkflowResponse
)
from backend.services import template_service, workflow_service

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=WorkflowTemplateResponse, status_code=201)
def create_template(
    template_data: WorkflowTemplateCreate,
    session: Session = Depends(get_session)
):
    """Create a new workflow template"""
    return template_service.create_template(session, template_data)


@router.get("", response_model=List[WorkflowTemplateResponse])
def get_templates(
    session: Session = Depends(get_session)
):
    """Get all templates"""
    return template_service.get_templates(session)


@router.get("/{template_id}", response_model=WorkflowTemplateResponse)
def get_template(
    template_id: str,
    session: Session = Depends(get_session)
):
    """Get template by ID"""
    return template_service.get_template(session, template_id)


@router.put("/{template_id}", response_model=WorkflowTemplateResponse)
def update_template(
    template_id: str,
    template_data: WorkflowTemplateUpdate,
    session: Session = Depends(get_session)
):
    """Update a template"""
    return template_service.update_template(session, template_id, template_data)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    session: Session = Depends(get_session)
):
    """Delete a template"""
    template_service.delete_template(session, template_id)
    return None


@router.post("/{template_id}/apply", response_model=WorkflowResponse, status_code=201)
def apply_template(
    template_id: str,
    apply_request: TemplateApplyRequest,
    session: Session = Depends(get_session)
):
    """Apply a template to create a new workflow"""
    from backend.schemas import WorkflowCreate, AgentCreate, DependencyCreate
    
    # Get template data
    template_data = template_service.apply_template(
        session,
        template_id,
        apply_request.workflow_name,
        apply_request.workflow_description,
        apply_request.overrides
    )
    
    # Create workflow
    workflow = workflow_service.create_workflow(
        session,
        WorkflowCreate(**template_data["workflow"])
    )
    
    # Create agents
    if template_data["agents"]:
        agents = [
            AgentCreate(**agent_data) for agent_data in template_data["agents"]
        ]
        workflow_service.update_agents(session, workflow.id, agents)
    
    # Create dependencies
    if template_data["dependencies"]:
        dependencies = [
            DependencyCreate(**dep_data) for dep_data in template_data["dependencies"]
        ]
        workflow_service.update_dependencies(session, workflow.id, dependencies)
    
    return workflow

