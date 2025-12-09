"""
Agent/Workflow runs router - List and get run details
"""

from fastapi import APIRouter, HTTPException, status, Depends
from src.database import get_db_connection
from src.dependencies import get_current_user_id
from src.schemas import RunResponse, RunListResponse, RunStatus
from src.services.logging_service import get_run_statistics
from uuid import UUID
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=List[RunListResponse])
async def list_runs(
    run_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """List all runs accessible to the current user."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, run_type, agent_id, workflow_id, status,
                       started_at, completed_at, created_at
                FROM agent_runs
                WHERE 1=1
            """
            params = []
            
            if run_type:
                query += " AND run_type = %s"
                params.append(run_type)
            
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


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Get a run by ID with full details."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, run_type, agent_id, workflow_id, status,
                       input_message, context_variables, output, error,
                       step_results, messages, tool_calls, tokens_used,
                       started_at, completed_at, owner_id, created_at
                FROM agent_runs
                WHERE id = %s
                """,
                (str(run_id),)
            )
            result = cur.fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Run not found"
                )
            
            return RunResponse(
                id=result['id'],
                run_type=result['run_type'],
                agent_id=result['agent_id'],
                workflow_id=result['workflow_id'],
                status=result['status'],
                input_message=result['input_message'],
                context_variables=result['context_variables'] or {},
                output=result['output'],
                error=result['error'],
                step_results=result['step_results'] or [],
                messages=result['messages'] or [],
                tool_calls=result['tool_calls'] or [],
                tokens_used=result['tokens_used'] or 0,
                started_at=result['started_at'],
                completed_at=result['completed_at'],
                owner_id=result['owner_id'],
                created_at=result['created_at']
            )


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Cancel a running execution."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            # First check if the run exists and is in a cancellable state
            cur.execute(
                "SELECT status FROM agent_runs WHERE id = %s",
                (str(run_id),)
            )
            result = cur.fetchone()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Run not found"
                )
            
            if result['status'] not in ['pending', 'running']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel run with status: {result['status']}"
                )
            
            # Update status to cancelled
            cur.execute(
                """
                UPDATE agent_runs
                SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, run_type, agent_id, workflow_id, status,
                          input_message, context_variables, output, error,
                          step_results, messages, tool_calls, tokens_used,
                          started_at, completed_at, owner_id, created_at
                """,
                (str(run_id),)
            )
            updated = cur.fetchone()
            conn.commit()
            
            return RunResponse(
                id=updated['id'],
                run_type=updated['run_type'],
                agent_id=updated['agent_id'],
                workflow_id=updated['workflow_id'],
                status=updated['status'],
                input_message=updated['input_message'],
                context_variables=updated['context_variables'] or {},
                output=updated['output'],
                error=updated['error'],
                step_results=updated['step_results'] or [],
                messages=updated['messages'] or [],
                tool_calls=updated['tool_calls'] or [],
                tokens_used=updated['tokens_used'] or 0,
                started_at=updated['started_at'],
                completed_at=updated['completed_at'],
                owner_id=updated['owner_id'],
                created_at=updated['created_at']
            )


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(
    run_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """Delete a run record."""
    with get_db_connection(str(current_user_id)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM agent_runs WHERE id = %s RETURNING id",
                (str(run_id),)
            )
            result = cur.fetchone()
            conn.commit()
            
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Run not found"
                )


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_runs_statistics(
    days: int = 30,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get run statistics for the current user.
    
    Args:
        days: Number of days to include in statistics (default: 30)
    """
    return get_run_statistics(str(current_user_id), days=days)
