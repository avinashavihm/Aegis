"""
Logging service for Aegis API - tracks agent runs and API requests
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from src.database import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('aegis')


class AegisLogger:
    """
    Logger for Aegis agent and workflow operations.
    """
    
    @staticmethod
    def log_agent_start(run_id: UUID, agent_name: str, user_id: str, input_message: str):
        """Log agent execution start"""
        logger.info(
            f"Agent Run Started | run_id={run_id} | agent={agent_name} | "
            f"user={user_id} | input_length={len(input_message)}"
        )
    
    @staticmethod
    def log_agent_complete(
        run_id: UUID,
        agent_name: str,
        user_id: str,
        status: str,
        duration_ms: float,
        tokens_used: int = 0
    ):
        """Log agent execution completion"""
        logger.info(
            f"Agent Run Completed | run_id={run_id} | agent={agent_name} | "
            f"user={user_id} | status={status} | duration_ms={duration_ms:.2f} | "
            f"tokens={tokens_used}"
        )
    
    @staticmethod
    def log_agent_error(run_id: UUID, agent_name: str, user_id: str, error: str):
        """Log agent execution error"""
        logger.error(
            f"Agent Run Failed | run_id={run_id} | agent={agent_name} | "
            f"user={user_id} | error={error}"
        )
    
    @staticmethod
    def log_workflow_start(run_id: UUID, workflow_name: str, user_id: str, step_count: int):
        """Log workflow execution start"""
        logger.info(
            f"Workflow Run Started | run_id={run_id} | workflow={workflow_name} | "
            f"user={user_id} | steps={step_count}"
        )
    
    @staticmethod
    def log_workflow_step(
        run_id: UUID,
        step_id: str,
        agent_name: str,
        status: str,
        duration_ms: float = 0
    ):
        """Log workflow step execution"""
        logger.info(
            f"Workflow Step | run_id={run_id} | step={step_id} | "
            f"agent={agent_name} | status={status} | duration_ms={duration_ms:.2f}"
        )
    
    @staticmethod
    def log_workflow_complete(
        run_id: UUID,
        workflow_name: str,
        user_id: str,
        status: str,
        duration_ms: float,
        steps_completed: int,
        steps_failed: int
    ):
        """Log workflow execution completion"""
        logger.info(
            f"Workflow Run Completed | run_id={run_id} | workflow={workflow_name} | "
            f"user={user_id} | status={status} | duration_ms={duration_ms:.2f} | "
            f"steps_completed={steps_completed} | steps_failed={steps_failed}"
        )
    
    @staticmethod
    def log_tool_call(run_id: UUID, tool_name: str, success: bool, duration_ms: float = 0):
        """Log tool call"""
        status = "success" if success else "failed"
        logger.debug(
            f"Tool Call | run_id={run_id} | tool={tool_name} | "
            f"status={status} | duration_ms={duration_ms:.2f}"
        )
    
    @staticmethod
    def log_api_request(
        method: str,
        path: str,
        user_id: Optional[str],
        status_code: int,
        duration_ms: float
    ):
        """Log API request"""
        logger.info(
            f"API Request | method={method} | path={path} | "
            f"user={user_id or 'anonymous'} | status={status_code} | "
            f"duration_ms={duration_ms:.2f}"
        )


def get_run_statistics(user_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Get run statistics for a user.
    
    Args:
        user_id: User ID to get statistics for
        days: Number of days to include in statistics
        
    Returns:
        Dictionary with run statistics
    """
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            # Total runs
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total_runs,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
                    COUNT(CASE WHEN run_type = 'agent' THEN 1 END) as agent_runs,
                    COUNT(CASE WHEN run_type = 'workflow' THEN 1 END) as workflow_runs,
                    COALESCE(SUM(tokens_used), 0) as total_tokens,
                    COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000), 0) as avg_duration_ms
                FROM agent_runs
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                """,
                (days,)
            )
            stats = cur.fetchone()
            
            # Runs per day
            cur.execute(
                """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as runs
                FROM agent_runs
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                """,
                (days,)
            )
            runs_per_day = [
                {"date": str(row['date']), "runs": row['runs']}
                for row in cur.fetchall()
            ]
            
            # Top agents by usage
            cur.execute(
                """
                SELECT 
                    a.name as agent_name,
                    COUNT(*) as run_count
                FROM agent_runs ar
                JOIN agents a ON ar.agent_id = a.id
                WHERE ar.created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY a.id, a.name
                ORDER BY run_count DESC
                LIMIT 5
                """,
                (days,)
            )
            top_agents = [
                {"agent_name": row['agent_name'], "run_count": row['run_count']}
                for row in cur.fetchall()
            ]
            
            return {
                "period_days": days,
                "total_runs": stats['total_runs'],
                "completed": stats['completed'],
                "failed": stats['failed'],
                "running": stats['running'],
                "agent_runs": stats['agent_runs'],
                "workflow_runs": stats['workflow_runs'],
                "total_tokens": int(stats['total_tokens']),
                "avg_duration_ms": float(stats['avg_duration_ms']),
                "success_rate": (
                    round(stats['completed'] / stats['total_runs'] * 100, 2)
                    if stats['total_runs'] > 0 else 0
                ),
                "runs_per_day": runs_per_day,
                "top_agents": top_agents
            }
