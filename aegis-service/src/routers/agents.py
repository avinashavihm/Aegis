"""
Agent management router - CRUD operations and execution
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from src.database import get_db_connection
from src.dependencies import get_current_user_id
from src.schemas import (
    AgentCreate, AgentUpdate, AgentResponse,
    RunCreate, RunResponse, RunListResponse, RunStatus, AgentCapabilitySchema
)
from uuid import UUID
import json
from datetime import datetime
from typing import List, Optional
from src.services.tool_registry import tool_registry

router = APIRouter(prefix="/agents", tags=["agents"])

DEFAULT_PREMIUM_CAPABILITIES = [
    AgentCapabilitySchema(
        name="web_search",
        description="Search, browse, and extract information from the web",
        keywords=["web", "search", "browse"],
        priority=10,
    ),
    AgentCapabilitySchema(
        name="file_ops",
        description="Read and write workspace files",
        keywords=["file", "document", "workspace"],
        priority=8,
    ),
    AgentCapabilitySchema(
        name="code_execution",
        description="Execute python and shell commands safely",
        keywords=["code", "python", "shell", "command"],
        priority=8,
    ),
    AgentCapabilitySchema(
        name="knowledge_and_store",
        description="Query connectors and agent store resources",
        keywords=["knowledge", "store", "connector", "crud"],
        priority=7,
    ),
    AgentCapabilitySchema(
        name="autonomous_planning",
        description="Plan and run tasks with autonomous tools",
        keywords=["plan", "autonomous", "workflow"],
        priority=6,
    ),
]


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    status_filter: Optional[str] = None,
    tag: Optional[str] = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List all agents accessible to the current user."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, name, description, model, instructions, tools,
                       custom_tool_ids, mcp_server_ids, file_ids,
                       tool_choice, parallel_tool_calls, capabilities,
                       autonomous_mode, tags, metadata, status, owner_id,
                       created_at, updated_at
                FROM agents
                WHERE 1=1
            """
            params = []
            
            if status_filter:
                query += " AND status = %s"
                params.append(status_filter)
            
            if tag:
                query += " AND tags ? %s"
                params.append(tag)
            
            query += " ORDER BY created_at DESC"
            
            cur.execute(query, params)
            agents = cur.fetchall()
            
            return [
                AgentResponse(
                    id=a['id'],
                    name=a['name'],
                    description=a['description'],
                    model=a['model'],
                    instructions=a['instructions'],
                    tools=a['tools'] or [],
                    custom_tool_ids=a.get('custom_tool_ids') or [],
                    mcp_server_ids=a.get('mcp_server_ids') or [],
                    file_ids=a.get('file_ids') or [],
                    tool_choice=a['tool_choice'],
                    parallel_tool_calls=a['parallel_tool_calls'],
                    capabilities=a['capabilities'] or [],
                    autonomous_mode=a['autonomous_mode'],
                    tags=a['tags'] or [],
                    metadata=a['metadata'] or {},
                    status=a['status'],
                    owner_id=a['owner_id'],
                    created_at=a['created_at'],
                    updated_at=a['updated_at']
                )
                for a in agents
            ]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create a new agent."""
    # Premium defaults: full toolset and permissive capabilities
    available_tools = tool_registry.get_tool_names()
    resolved_tools = agent.tools or available_tools
    resolved_tool_choice = agent.tool_choice or "auto"
    resolved_parallel = True if agent.parallel_tool_calls is None else agent.parallel_tool_calls
    resolved_autonomous = True if agent.autonomous_mode is None else agent.autonomous_mode
    resolved_caps = agent.capabilities or DEFAULT_PREMIUM_CAPABILITIES
    resolved_metadata = {"profile": "premium", **(agent.metadata or {})}
    resolved_tags = agent.tags[:] if agent.tags else []
    if "premium" not in {t.lower() for t in resolved_tags}:
        resolved_tags.append("premium")
    status_value = agent.status.value if hasattr(agent.status, "value") else agent.status

    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agents (
                    name, description, model, instructions, tools,
                    custom_tool_ids, mcp_server_ids, file_ids,
                    tool_choice, parallel_tool_calls, capabilities,
                    autonomous_mode, tags, metadata, status, owner_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, model, instructions, tools,
                          custom_tool_ids, mcp_server_ids, file_ids,
                          tool_choice, parallel_tool_calls, capabilities,
                          autonomous_mode, tags, metadata, status, owner_id,
                          created_at, updated_at
                """,
                (
                    agent.name,
                    agent.description,
                    agent.model,
                    agent.instructions,
                    json.dumps(resolved_tools),
                    json.dumps(agent.custom_tool_ids),
                    json.dumps(agent.mcp_server_ids),
                    json.dumps(agent.file_ids),
                    resolved_tool_choice,
                    resolved_parallel,
                    json.dumps([c.model_dump() for c in resolved_caps]),
                    resolved_autonomous,
                    json.dumps(resolved_tags),
                    json.dumps(resolved_metadata),
                    status_value,
                    str(current_user_id)
                )
            )
            result = cur.fetchone()
            conn.commit()
            
            return AgentResponse(
                id=result['id'],
                name=result['name'],
                description=result['description'],
                model=result['model'],
                instructions=result['instructions'],
                tools=result['tools'] or [],
                custom_tool_ids=result.get('custom_tool_ids') or [],
                mcp_server_ids=result.get('mcp_server_ids') or [],
                file_ids=result.get('file_ids') or [],
                tool_choice=result['tool_choice'],
                parallel_tool_calls=result['parallel_tool_calls'],
                capabilities=result['capabilities'] or [],
                autonomous_mode=result['autonomous_mode'],
                tags=result['tags'] or [],
                metadata=result['metadata'] or {},
                status=result['status'],
                owner_id=result['owner_id'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get an agent by ID."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, model, instructions, tools,
                       custom_tool_ids, mcp_server_ids, file_ids,
                       tool_choice, parallel_tool_calls, capabilities,
                       autonomous_mode, tags, metadata, status, owner_id,
                       created_at, updated_at
                FROM agents
                WHERE id = %s
                """,
                (str(agent_id),)
            )
            result = cur.fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            return AgentResponse(
                id=result['id'],
                name=result['name'],
                description=result['description'],
                model=result['model'],
                instructions=result['instructions'],
                tools=result['tools'] or [],
                custom_tool_ids=result.get('custom_tool_ids') or [],
                mcp_server_ids=result.get('mcp_server_ids') or [],
                file_ids=result.get('file_ids') or [],
                tool_choice=result['tool_choice'],
                parallel_tool_calls=result['parallel_tool_calls'],
                capabilities=result['capabilities'] or [],
                autonomous_mode=result['autonomous_mode'],
                tags=result['tags'] or [],
                metadata=result['metadata'] or {},
                status=result['status'],
                owner_id=result['owner_id'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Update an agent."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Build dynamic update query
            update_fields = []
            params = []
            
            if agent_update.name is not None:
                update_fields.append("name = %s")
                params.append(agent_update.name)
            if agent_update.description is not None:
                update_fields.append("description = %s")
                params.append(agent_update.description)
            if agent_update.model is not None:
                update_fields.append("model = %s")
                params.append(agent_update.model)
            if agent_update.instructions is not None:
                update_fields.append("instructions = %s")
                params.append(agent_update.instructions)
            if agent_update.tools is not None:
                update_fields.append("tools = %s")
                params.append(json.dumps(agent_update.tools))
            if agent_update.custom_tool_ids is not None:
                update_fields.append("custom_tool_ids = %s")
                params.append(json.dumps(agent_update.custom_tool_ids))
            if agent_update.mcp_server_ids is not None:
                update_fields.append("mcp_server_ids = %s")
                params.append(json.dumps(agent_update.mcp_server_ids))
            if agent_update.file_ids is not None:
                update_fields.append("file_ids = %s")
                params.append(json.dumps(agent_update.file_ids))
            if agent_update.tool_choice is not None:
                update_fields.append("tool_choice = %s")
                params.append(agent_update.tool_choice)
            if agent_update.parallel_tool_calls is not None:
                update_fields.append("parallel_tool_calls = %s")
                params.append(agent_update.parallel_tool_calls)
            if agent_update.capabilities is not None:
                update_fields.append("capabilities = %s")
                params.append(json.dumps([c.model_dump() for c in agent_update.capabilities]))
            if agent_update.autonomous_mode is not None:
                update_fields.append("autonomous_mode = %s")
                params.append(agent_update.autonomous_mode)
            if agent_update.tags is not None:
                update_fields.append("tags = %s")
                params.append(json.dumps(agent_update.tags))
            if agent_update.metadata is not None:
                update_fields.append("metadata = %s")
                params.append(json.dumps(agent_update.metadata))
            if agent_update.status is not None:
                update_fields.append("status = %s")
                params.append(agent_update.status.value)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            params.append(str(agent_id))
            
            cur.execute(
                f"""
                UPDATE agents
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, name, description, model, instructions, tools,
                          custom_tool_ids, mcp_server_ids, file_ids,
                          tool_choice, parallel_tool_calls, capabilities,
                          autonomous_mode, tags, metadata, status, owner_id,
                          created_at, updated_at
                """,
                params
            )
            result = cur.fetchone()
            conn.commit()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            return AgentResponse(
                id=result['id'],
                name=result['name'],
                description=result['description'],
                model=result['model'],
                instructions=result['instructions'],
                tools=result['tools'] or [],
                custom_tool_ids=result.get('custom_tool_ids') or [],
                mcp_server_ids=result.get('mcp_server_ids') or [],
                file_ids=result.get('file_ids') or [],
                tool_choice=result['tool_choice'],
                parallel_tool_calls=result['parallel_tool_calls'],
                capabilities=result['capabilities'] or [],
                autonomous_mode=result['autonomous_mode'],
                tags=result['tags'] or [],
                metadata=result['metadata'] or {},
                status=result['status'],
                owner_id=result['owner_id'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete an agent."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM agents WHERE id = %s RETURNING id",
                (str(agent_id),)
            )
            result = cur.fetchone()
            conn.commit()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )


@router.post("/{agent_id}/run", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def run_agent(
    agent_id: UUID,
    run_request: RunCreate,
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Execute an agent with the given input."""
    from src.services.runner import AgentRunner
    
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Get agent
            cur.execute(
                """
                SELECT id, name, description, model, instructions, tools,
                       custom_tool_ids, mcp_server_ids, file_ids,
                       tool_choice, parallel_tool_calls, capabilities,
                       autonomous_mode, tags, metadata, status
                FROM agents
                WHERE id = %s
                """,
                (str(agent_id),)
            )
            agent_data = cur.fetchone()
            
            if not agent_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            if agent_data['status'] != 'active':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Agent is not active (status: {agent_data['status']})"
                )
            
            # Create run record
            cur.execute(
                """
                INSERT INTO agent_runs (
                    run_type, agent_id, status, input_message,
                    context_variables, owner_id
                ) VALUES ('agent', %s, 'pending', %s, %s, %s)
                RETURNING id, run_type, agent_id, workflow_id, status,
                          input_message, context_variables, output, error,
                          step_results, messages, tool_calls, tokens_used,
                          started_at, completed_at, owner_id, created_at
                """,
                (
                    str(agent_id),
                    run_request.input_message,
                    json.dumps(run_request.context_variables),
                    str(current_user_id)
                )
            )
            run_record = cur.fetchone()
            conn.commit()
    
    # Execute agent in background
    runner = AgentRunner()
    background_tasks.add_task(
        runner.execute_agent,
        run_id=run_record['id'],
        agent_data=dict(agent_data),
        input_message=run_request.input_message,
        context_variables=run_request.context_variables,
        model_override=run_request.model_override,
        max_turns=run_request.max_turns,
        user_id=str(current_user_id)
    )
    
    return RunResponse(
        id=run_record['id'],
        run_type=run_record['run_type'],
        agent_id=run_record['agent_id'],
        workflow_id=run_record['workflow_id'],
        status=run_record['status'],
        input_message=run_record['input_message'],
        context_variables=run_record['context_variables'] or {},
        output=run_record['output'],
        error=run_record['error'],
        step_results=run_record['step_results'] or [],
        messages=run_record['messages'] or [],
        tool_calls=run_record['tool_calls'] or [],
        tokens_used=run_record['tokens_used'] or 0,
        started_at=run_record['started_at'],
        completed_at=run_record['completed_at'],
        owner_id=run_record['owner_id'],
        created_at=run_record['created_at']
    )


@router.get("/{agent_id}/runs", response_model=List[RunListResponse])
async def list_agent_runs(
    agent_id: UUID,
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List runs for a specific agent."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, run_type, agent_id, workflow_id, status,
                       started_at, completed_at, created_at
                FROM agent_runs
                WHERE agent_id = %s
            """
            params = [str(agent_id)]
            
            if status_filter:
                query += " AND status = %s"
                params.append(status_filter)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            runs = cur.fetchall()
            
            return [
                RunListResponse(
                    id=r['id'],
                    run_type=r['run_type'],
                    agent_id=r['agent_id'],
                    workflow_id=r['workflow_id'],
                    status=r['status'],
                    started_at=r['started_at'],
                    completed_at=r['completed_at'],
                    created_at=r['created_at']
                )
                for r in runs
            ]
