"""Monitoring router for metrics and health endpoints"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from typing import Optional
from backend.database import get_session
from backend.services import monitoring_service

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics")
def get_metrics(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    time_range_hours: Optional[int] = Query(24, description="Time range in hours"),
    session: Session = Depends(get_session)
):
    """Get execution metrics"""
    metrics = monitoring_service.get_execution_metrics(
        session,
        workflow_id=workflow_id,
        time_range_hours=time_range_hours
    )
    return metrics.to_dict()


@router.get("/agent/{agent_id}/health")
def get_agent_health(
    agent_id: str,
    session: Session = Depends(get_session)
):
    """Get health status for an agent"""
    health = monitoring_service.get_agent_health(session, agent_id)
    if not health:
        return {"error": "Agent not found"}
    return health.to_dict()


@router.get("/agents/health")
def get_all_agents_health(
    session: Session = Depends(get_session)
):
    """Get health status for all agents"""
    health_statuses = monitoring_service.get_all_agents_health(session)
    return [h.to_dict() for h in health_statuses]


@router.get("/performance")
def get_performance_metrics(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    time_range_hours: int = Query(24, description="Time range in hours"),
    session: Session = Depends(get_session)
):
    """Get performance metrics (throughput, latency, error rate)"""
    return monitoring_service.get_performance_metrics(
        session,
        workflow_id=workflow_id,
        time_range_hours=time_range_hours
    )


@router.get("/dashboard")
def get_dashboard_data(
    session: Session = Depends(get_session)
):
    """Get dashboard data combining metrics, health, and performance"""
    metrics = monitoring_service.get_execution_metrics(session)
    agents_health = monitoring_service.get_all_agents_health(session)
    performance = monitoring_service.get_performance_metrics(session)
    
    return {
        "metrics": metrics.to_dict(),
        "agents_health": [h.to_dict() for h in agents_health],
        "performance": performance
    }

