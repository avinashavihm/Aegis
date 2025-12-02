import json
import yaml
from typing import Dict, Any, Optional
from sqlmodel import Session
from backend.models import Workflow, Agent, AgentDependency
from backend.services import workflow_service


def export_workflow_to_dict(session: Session, workflow_id: str) -> Dict[str, Any]:
    """Export workflow to dictionary format"""
    workflow = workflow_service.get_workflow(session, workflow_id)
    agents = workflow_service.get_agents(session, workflow_id)
    dependencies = workflow_service.get_dependencies(session, workflow_id)
    
    return {
        "workflow": {
            "name": workflow.name,
            "description": workflow.description,
        },
        "agents": [
            {
                "name": agent.name,
                "role": agent.role,
                "agent_properties": agent.agent_properties,
                "agent_capabilities": agent.agent_capabilities,
                "agent_status": agent.agent_status,
            }
            for agent in agents
        ],
        "dependencies": [
            {
                "agent_id": dep.agent_id,
                "depends_on_agent_id": dep.depends_on_agent_id,
            }
            for dep in dependencies
        ],
        "metadata": {
            "exported_at": workflow.updated_at.isoformat(),
            "workflow_id": workflow.id,
        }
    }


def export_workflow_to_json(session: Session, workflow_id: str) -> str:
    """Export workflow to JSON string"""
    data = export_workflow_to_dict(session, workflow_id)
    return json.dumps(data, indent=2, default=str)


def export_workflow_to_yaml(session: Session, workflow_id: str) -> str:
    """Export workflow to YAML string"""
    data = export_workflow_to_dict(session, workflow_id)
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def import_workflow_from_dict(
    session: Session,
    data: Dict[str, Any],
    workflow_name: Optional[str] = None,
    workflow_description: Optional[str] = None
) -> Workflow:
    """
    Import workflow from dictionary format.
    Creates a new workflow with the imported data.
    """
    from backend.schemas import WorkflowCreate, AgentCreate, DependencyCreate
    from backend.services import workflow_service
    
    # Extract workflow data
    workflow_data = data.get("workflow", {})
    workflow_name = workflow_name or workflow_data.get("name", "Imported Workflow")
    workflow_description = workflow_description or workflow_data.get("description", "")
    
    # Create workflow
    workflow = workflow_service.create_workflow(
        session,
        WorkflowCreate(name=workflow_name, description=workflow_description)
    )
    
    # Import agents
    agents_data = data.get("agents", [])
    if agents_data:
        agent_creates = []
        agent_id_mapping = {}  # Map old agent IDs to new ones
        
        for idx, agent_data in enumerate(agents_data):
            # Create agent with imported data
            agent_create = AgentCreate(
                name=agent_data.get("name", f"Agent {idx + 1}"),
                role=agent_data.get("role", "executor"),
                agent_properties=agent_data.get("agent_properties"),
                agent_capabilities=agent_data.get("agent_capabilities"),
                agent_status=agent_data.get("agent_status", "active"),
            )
            agent_creates.append(agent_create)
        
        # Create agents
        created_agents = workflow_service.update_agents(session, workflow.id, agent_creates)
        
        # Build mapping if original IDs are provided (for dependencies)
        for old_agent_data, new_agent in zip(agents_data, created_agents):
            old_id = old_agent_data.get("id")
            if old_id:
                agent_id_mapping[old_id] = new_agent.id
        
        # Import dependencies
        dependencies_data = data.get("dependencies", [])
        if dependencies_data:
            dep_creates = []
            for dep_data in dependencies_data:
                old_agent_id = dep_data.get("agent_id")
                old_depends_on_id = dep_data.get("depends_on_agent_id")
                
                # Map old IDs to new IDs
                new_agent_id = agent_id_mapping.get(old_agent_id)
                new_depends_on_id = agent_id_mapping.get(old_depends_on_id)
                
                if new_agent_id and new_depends_on_id:
                    dep_creates.append(
                        DependencyCreate(
                            agent_id=new_agent_id,
                            depends_on_agent_id=new_depends_on_id
                        )
                    )
            
            if dep_creates:
                workflow_service.update_dependencies(session, workflow.id, dep_creates)
    
    return workflow


def import_workflow_from_json(session: Session, json_str: str, **kwargs) -> Workflow:
    """Import workflow from JSON string"""
    data = json.loads(json_str)
    return import_workflow_from_dict(session, data, **kwargs)


def import_workflow_from_yaml(session: Session, yaml_str: str, **kwargs) -> Workflow:
    """Import workflow from YAML string"""
    data = yaml.safe_load(yaml_str)
    return import_workflow_from_dict(session, data, **kwargs)

