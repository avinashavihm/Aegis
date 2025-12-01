"""Agent router for individual agent operations"""
from fastapi import APIRouter, Depends
from sqlmodel import Session
from backend.database import get_session
from backend.schemas import AgentResponse, AgentUpdate
from backend.services import workflow_service

router = APIRouter(prefix="/workflow/{workflow_id}/agents", tags=["agents"])


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    workflow_id: str,
    agent_id: str,
    agent_data: AgentUpdate,
    session: Session = Depends(get_session)
):
    """Update an individual agent"""
    return workflow_service.update_agent(session, workflow_id, agent_id, agent_data)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    workflow_id: str,
    agent_id: str,
    session: Session = Depends(get_session)
):
    """Delete an individual agent"""
    workflow_service.delete_agent(session, workflow_id, agent_id)
    return None

