from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from backend.models import WorkflowTemplate
from backend.schemas import WorkflowTemplateCreate, WorkflowTemplateUpdate
from backend.exceptions import TemplateNotFoundError


def create_template(session: Session, template_data: WorkflowTemplateCreate) -> WorkflowTemplate:
    """Create a new workflow template"""
    template = WorkflowTemplate(**template_data.dict())
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def get_template(session: Session, template_id: str) -> WorkflowTemplate:
    """Get template by ID"""
    template = session.get(WorkflowTemplate, template_id)
    if not template:
        raise TemplateNotFoundError(template_id)
    return template


def get_templates(session: Session) -> List[WorkflowTemplate]:
    """Get all templates"""
    statement = select(WorkflowTemplate).order_by(WorkflowTemplate.created_at.desc())
    return list(session.exec(statement).all())


def update_template(
    session: Session,
    template_id: str,
    template_data: WorkflowTemplateUpdate
) -> WorkflowTemplate:
    """Update a template"""
    template = get_template(session, template_id)
    
    update_data = template_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    template.updated_at = datetime.utcnow()
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def delete_template(session: Session, template_id: str) -> None:
    """Delete a template"""
    template = get_template(session, template_id)
    session.delete(template)
    session.commit()


def apply_template(
    session: Session,
    template_id: str,
    workflow_name: str,
    workflow_description: Optional[str] = None,
    overrides: Optional[dict] = None
) -> dict:
    """
    Apply a template to create workflow data.
    Returns a dict with workflow, agents, and dependencies data.
    """
    template = get_template(session, template_id)
    template_data = template.template_data.copy()
    
    # Apply overrides if provided
    if overrides:
        template_data.update(overrides)
    
    # Extract workflow data
    workflow_data = {
        "name": workflow_name,
        "description": workflow_description or template.description or "",
    }
    
    # Extract agents and dependencies from template
    agents = template_data.get("agents", [])
    dependencies = template_data.get("dependencies", [])
    
    return {
        "workflow": workflow_data,
        "agents": agents,
        "dependencies": dependencies
    }

