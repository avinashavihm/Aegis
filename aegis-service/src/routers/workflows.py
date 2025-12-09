"""
Workflow management router - CRUD operations and execution
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from src.database import get_db_connection
from src.dependencies import get_current_user_id
from src.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    RunCreate, RunResponse, RunListResponse, RunStatus
)
from uuid import UUID
import json
from datetime import datetime
from typing import List, Optional

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    status_filter: Optional[str] = None,
    tag: Optional[str] = None,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List all workflows accessible to the current user."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, name, description, steps, execution_mode,
                       tags, metadata, status, owner_id, created_at, updated_at
                FROM workflows
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
            workflows = cur.fetchall()
            
            return [
                WorkflowResponse(
                    id=w['id'],
                    name=w['name'],
                    description=w['description'],
                    steps=w['steps'] or [],
                    execution_mode=w['execution_mode'],
                    tags=w['tags'] or [],
                    metadata=w['metadata'] or {},
                    status=w['status'],
                    owner_id=w['owner_id'],
                    created_at=w['created_at'],
                    updated_at=w['updated_at']
                )
                for w in workflows
            ]


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow: WorkflowCreate,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Create a new workflow."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflows (
                    name, description, steps, execution_mode,
                    tags, metadata, status, owner_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, description, steps, execution_mode,
                          tags, metadata, status, owner_id, created_at, updated_at
                """,
                (
                    workflow.name,
                    workflow.description,
                    json.dumps([s.model_dump() for s in workflow.steps]),
                    workflow.execution_mode.value,
                    json.dumps(workflow.tags),
                    json.dumps(workflow.metadata),
                    workflow.status.value,
                    str(current_user_id)
                )
            )
            result = cur.fetchone()
            conn.commit()
            
            return WorkflowResponse(
                id=result['id'],
                name=result['name'],
                description=result['description'],
                steps=result['steps'] or [],
                execution_mode=result['execution_mode'],
                tags=result['tags'] or [],
                metadata=result['metadata'] or {},
                status=result['status'],
                owner_id=result['owner_id'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get a workflow by ID."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, steps, execution_mode,
                       tags, metadata, status, owner_id, created_at, updated_at
                FROM workflows
                WHERE id = %s
                """,
                (str(workflow_id),)
            )
            result = cur.fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )
            
            return WorkflowResponse(
                id=result['id'],
                name=result['name'],
                description=result['description'],
                steps=result['steps'] or [],
                execution_mode=result['execution_mode'],
                tags=result['tags'] or [],
                metadata=result['metadata'] or {},
                status=result['status'],
                owner_id=result['owner_id'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_update: WorkflowUpdate,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Update a workflow."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Build dynamic update query
            update_fields = []
            params = []
            
            if workflow_update.name is not None:
                update_fields.append("name = %s")
                params.append(workflow_update.name)
            if workflow_update.description is not None:
                update_fields.append("description = %s")
                params.append(workflow_update.description)
            if workflow_update.steps is not None:
                update_fields.append("steps = %s")
                params.append(json.dumps([s.model_dump() for s in workflow_update.steps]))
            if workflow_update.execution_mode is not None:
                update_fields.append("execution_mode = %s")
                params.append(workflow_update.execution_mode.value)
            if workflow_update.tags is not None:
                update_fields.append("tags = %s")
                params.append(json.dumps(workflow_update.tags))
            if workflow_update.metadata is not None:
                update_fields.append("metadata = %s")
                params.append(json.dumps(workflow_update.metadata))
            if workflow_update.status is not None:
                update_fields.append("status = %s")
                params.append(workflow_update.status.value)
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            params.append(str(workflow_id))
            
            cur.execute(
                f"""
                UPDATE workflows
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING id, name, description, steps, execution_mode,
                          tags, metadata, status, owner_id, created_at, updated_at
                """,
                params
            )
            result = cur.fetchone()
            conn.commit()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )
            
            return WorkflowResponse(
                id=result['id'],
                name=result['name'],
                description=result['description'],
                steps=result['steps'] or [],
                execution_mode=result['execution_mode'],
                tags=result['tags'] or [],
                metadata=result['metadata'] or {},
                status=result['status'],
                owner_id=result['owner_id'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a workflow."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM workflows WHERE id = %s RETURNING id",
                (str(workflow_id),)
            )
            result = cur.fetchone()
            conn.commit()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )


@router.post("/{workflow_id}/run", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def run_workflow(
    workflow_id: UUID,
    run_request: RunCreate,
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Execute a workflow with the given input."""
    from src.services.runner import AgentRunner
    
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # Get workflow
            cur.execute(
                """
                SELECT id, name, description, steps, execution_mode,
                       tags, metadata, status
                FROM workflows
                WHERE id = %s
                """,
                (str(workflow_id),)
            )
            workflow_data = cur.fetchone()
            
            if not workflow_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workflow not found"
                )
            
            if workflow_data['status'] != 'active':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Workflow is not active (status: {workflow_data['status']})"
                )
            
            # Get agents for each step
            steps = workflow_data['steps'] or []
            agent_ids = [step['agent_id'] for step in steps if step.get('agent_id')]
            
            if agent_ids:
                placeholders = ','.join(['%s'] * len(agent_ids))
                cur.execute(
                    f"""
                    SELECT id, name, description, model, instructions, tools,
                           tool_choice, parallel_tool_calls, capabilities,
                           autonomous_mode, tags, metadata, status
                    FROM agents
                    WHERE id IN ({placeholders})
                    """,
                    agent_ids
                )
                agents_data = {str(a['id']): dict(a) for a in cur.fetchall()}
            else:
                agents_data = {}
            
            # Create run record
            cur.execute(
                """
                INSERT INTO agent_runs (
                    run_type, workflow_id, status, input_message,
                    context_variables, owner_id
                ) VALUES ('workflow', %s, 'pending', %s, %s, %s)
                RETURNING id, run_type, agent_id, workflow_id, status,
                          input_message, context_variables, output, error,
                          step_results, messages, tool_calls, tokens_used,
                          started_at, completed_at, owner_id, created_at
                """,
                (
                    str(workflow_id),
                    run_request.input_message,
                    json.dumps(run_request.context_variables),
                    str(current_user_id)
                )
            )
            run_record = cur.fetchone()
            conn.commit()
    
    # Execute workflow in background
    runner = AgentRunner()
    background_tasks.add_task(
        runner.execute_workflow,
        run_id=run_record['id'],
        workflow_data=dict(workflow_data),
        agents_data=agents_data,
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


@router.get("/{workflow_id}/runs", response_model=List[RunListResponse])
async def list_workflow_runs(
    workflow_id: UUID,
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List runs for a specific workflow."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, run_type, agent_id, workflow_id, status,
                       started_at, completed_at, created_at
                FROM agent_runs
                WHERE workflow_id = %s
            """
            params = [str(workflow_id)]
            
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
