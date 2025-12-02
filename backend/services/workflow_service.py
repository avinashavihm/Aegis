from sqlmodel import Session, select, func, or_
from typing import List, Dict, Set, Optional
from datetime import datetime
from backend.models import Workflow, Agent, AgentDependency
from backend.schemas import (
    WorkflowCreate, WorkflowUpdate, AgentCreate, AgentUpdate, DependencyCreate,
    AgentsUpdateRequest, DependenciesUpdateRequest, WorkflowListResponse
)
from backend.exceptions import (
    WorkflowNotFoundError, AgentNotFoundError, DependencyCycleError
)


def create_workflow(session: Session, workflow_data: WorkflowCreate) -> Workflow:
    """Create a new workflow"""
    workflow = Workflow(**workflow_data.dict())
    session.add(workflow)
    session.commit()
    session.refresh(workflow)
    return workflow


def get_workflow(session: Session, workflow_id: str, include_deleted: bool = False) -> Workflow:
    """Get workflow by ID"""
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise WorkflowNotFoundError(workflow_id)
    if not include_deleted and workflow.deleted_at is not None:
        raise WorkflowNotFoundError(workflow_id)
    return workflow


def get_workflows(session: Session) -> List[Workflow]:
    """Get all workflows (non-deleted)"""
    statement = select(Workflow).where(Workflow.deleted_at.is_(None))
    return list(session.exec(statement).all())


def update_workflow(
    session: Session,
    workflow_id: str,
    workflow_data: WorkflowUpdate
) -> Workflow:
    """Update a workflow"""
    workflow = get_workflow(session, workflow_id)
    
    update_data = workflow_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)
    
    workflow.updated_at = datetime.utcnow()
    session.add(workflow)
    session.commit()
    session.refresh(workflow)
    return workflow


def delete_workflow(session: Session, workflow_id: str) -> None:
    """Soft delete a workflow"""
    workflow = get_workflow(session, workflow_id)
    workflow.deleted_at = datetime.utcnow()
    workflow.updated_at = datetime.utcnow()
    session.add(workflow)
    session.commit()


def get_workflows_paginated(
    session: Session,
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    sort: Optional[str] = None
) -> WorkflowListResponse:
    """Get workflows with pagination, search, and sorting"""
    # Base query - exclude deleted
    statement = select(Workflow).where(Workflow.deleted_at.is_(None))
    
    # Apply search filter
    if search:
        search_filter = or_(
            Workflow.name.ilike(f"%{search}%"),
            Workflow.description.ilike(f"%{search}%")
        )
        statement = statement.where(search_filter)
    
    # Get total count
    count_statement = select(func.count()).select_from(Workflow).where(Workflow.deleted_at.is_(None))
    if search:
        count_statement = count_statement.where(search_filter)
    total = session.exec(count_statement).one()
    
    # Apply sorting
    if sort:
        if sort == "name":
            statement = statement.order_by(Workflow.name)
        elif sort == "created_at":
            statement = statement.order_by(Workflow.created_at.desc())
        elif sort == "updated_at":
            statement = statement.order_by(Workflow.updated_at.desc())
    else:
        statement = statement.order_by(Workflow.created_at.desc())
    
    # Apply pagination
    offset = (page - 1) * limit
    statement = statement.offset(offset).limit(limit)
    
    items = list(session.exec(statement).all())
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return WorkflowListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages
    )


def get_agents(session: Session, workflow_id: str, include_deleted: bool = False) -> List[Agent]:
    """Get all agents for a workflow"""
    # Verify workflow exists
    get_workflow(session, workflow_id)
    
    statement = select(Agent).where(Agent.workflow_id == workflow_id)
    if not include_deleted:
        statement = statement.where(Agent.deleted_at.is_(None))
    return list(session.exec(statement).all())


def get_agent(session: Session, workflow_id: str, agent_id: str) -> Agent:
    """Get a single agent by ID"""
    # Verify workflow exists
    get_workflow(session, workflow_id)
    
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.workflow_id == workflow_id,
        Agent.deleted_at.is_(None)
    )
    agent = session.exec(statement).first()
    if not agent:
        raise AgentNotFoundError(agent_id)
    return agent


def update_agent(
    session: Session,
    workflow_id: str,
    agent_id: str,
    agent_data: AgentUpdate
) -> Agent:
    """Update an individual agent"""
    agent = get_agent(session, workflow_id, agent_id)
    
    update_data = agent_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    agent.updated_at = datetime.utcnow()
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def delete_agent(session: Session, workflow_id: str, agent_id: str) -> None:
    """Soft delete an individual agent"""
    agent = get_agent(session, workflow_id, agent_id)
    agent.deleted_at = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    session.add(agent)
    session.commit()


def update_agents(session: Session, workflow_id: str, agents_data: List[AgentCreate]) -> List[Agent]:
    """Update agents for a workflow (replace all existing agents)"""
    # Verify workflow exists
    get_workflow(session, workflow_id)
    
    # Delete existing agents
    statement = select(Agent).where(Agent.workflow_id == workflow_id)
    existing_agents = list(session.exec(statement).all())
    for agent in existing_agents:
        session.delete(agent)
    
    # Create new agents
    new_agents = []
    for agent_data in agents_data:
        agent = Agent(workflow_id=workflow_id, **agent_data.dict())
        session.add(agent)
        new_agents.append(agent)
    
    session.commit()
    for agent in new_agents:
        session.refresh(agent)
    
    return new_agents


def get_dependencies(session: Session, workflow_id: str) -> List[AgentDependency]:
    """Get all dependencies for a workflow"""
    # Verify workflow exists
    get_workflow(session, workflow_id)
    
    statement = select(AgentDependency).where(AgentDependency.workflow_id == workflow_id)
    return list(session.exec(statement).all())


def has_cycle(workflow_id: str, dependencies: List[DependencyCreate], session: Session) -> bool:
    """Check if the dependency graph has a cycle using DFS"""
    # Build adjacency list
    graph: Dict[str, List[str]] = {}
    all_agent_ids: Set[str] = set()
    
    # Get all agent IDs in the workflow
    agents = get_agents(session, workflow_id)
    agent_ids = {agent.id for agent in agents}
    
    # Build graph
    for dep in dependencies:
        if dep.agent_id not in graph:
            graph[dep.agent_id] = []
        graph[dep.agent_id].append(dep.depends_on_agent_id)
        all_agent_ids.add(dep.agent_id)
        all_agent_ids.add(dep.depends_on_agent_id)
    
    # Verify all referenced agents exist
    for agent_id in all_agent_ids:
        if agent_id not in agent_ids:
            raise AgentNotFoundError(agent_id)
    
    # DFS to detect cycles
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    
    def dfs(node: str) -> bool:
        """DFS helper to detect cycles"""
        if node in rec_stack:
            return True  # Cycle detected
        if node in visited:
            return False
        
        visited.add(node)
        rec_stack.add(node)
        
        # Check all neighbors
        for neighbor in graph.get(node, []):
            if dfs(neighbor):
                return True
        
        rec_stack.remove(node)
        return False
    
    # Check all nodes
    for node in all_agent_ids:
        if node not in visited:
            if dfs(node):
                return True
    
    return False


def update_dependencies(
    session: Session,
    workflow_id: str,
    dependencies_data: List[DependencyCreate]
) -> List[AgentDependency]:
    """Update dependencies for a workflow with cycle validation"""
    # Verify workflow exists
    get_workflow(session, workflow_id)
    
    # Check for cycles
    if has_cycle(workflow_id, dependencies_data, session):
        raise DependencyCycleError()
    
    # Delete existing dependencies
    statement = select(AgentDependency).where(AgentDependency.workflow_id == workflow_id)
    existing_deps = list(session.exec(statement).all())
    for dep in existing_deps:
        session.delete(dep)
    
    # Create new dependencies
    new_dependencies = []
    for dep_data in dependencies_data:
        dependency = AgentDependency(workflow_id=workflow_id, **dep_data.dict())
        session.add(dependency)
        new_dependencies.append(dependency)
    
    session.commit()
    for dep in new_dependencies:
        session.refresh(dep)
    
    return new_dependencies

