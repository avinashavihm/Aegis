"""Service for handling errors and notifications"""
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import logging
from backend.models import WorkflowExecution, AgentExecution

logger = logging.getLogger(__name__)

# Error notification hooks (can be extended with actual integrations)
_error_notification_hooks: List[Callable[[Dict[str, Any]], None]] = []


def register_error_notification_hook(hook: Callable[[Dict[str, Any]], None]) -> None:
    """Register a hook to be called when errors occur"""
    _error_notification_hooks.append(hook)


def notify_error(
    error_type: str,
    message: str,
    execution: Optional[WorkflowExecution] = None,
    agent_execution: Optional[AgentExecution] = None,
    error_details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Notify registered hooks about an error.
    
    Args:
        error_type: Type of error (e.g., 'execution_failed', 'agent_failed', 'retry_exhausted')
        message: Error message
        execution: Optional workflow execution context
        agent_execution: Optional agent execution context
        error_details: Additional error details
    """
    notification = {
        "error_type": error_type,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "execution_id": execution.id if execution else None,
        "workflow_id": execution.workflow_id if execution else None,
        "agent_execution_id": agent_execution.id if agent_execution else None,
        "agent_id": agent_execution.agent_id if agent_execution else None,
        "error_details": error_details or {}
    }
    
    # Log the error
    logger.error(
        f"Error notification: {error_type} - {message}",
        extra=notification
    )
    
    # Call registered hooks
    for hook in _error_notification_hooks:
        try:
            hook(notification)
        except Exception as e:
            logger.error(f"Error in notification hook: {e}", exc_info=True)


def create_fallback_action(
    action_type: str,
    action_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a fallback action configuration.
    
    Args:
        action_type: Type of fallback (e.g., 'retry', 'skip', 'use_default', 'notify')
        action_config: Configuration for the action
    
    Returns:
        Fallback action dictionary
    """
    return {
        "type": action_type,
        "config": action_config,
        "created_at": datetime.utcnow().isoformat()
    }


def execute_fallback_action(
    fallback_action: Dict[str, Any],
    context: Dict[str, Any]
) -> Any:
    """
    Execute a fallback action.
    
    Args:
        fallback_action: Fallback action configuration
        context: Execution context
    
    Returns:
        Result of fallback action
    """
    action_type = fallback_action.get("type")
    action_config = fallback_action.get("config", {})
    
    if action_type == "retry":
        # Retry logic is handled by retry_with_backoff
        return {"action": "retry", "config": action_config}
    elif action_type == "skip":
        return {"action": "skip", "message": "Skipping failed step"}
    elif action_type == "use_default":
        default_value = action_config.get("default_value")
        return {"action": "use_default", "value": default_value}
    elif action_type == "notify":
        notify_error(
            error_type="fallback_triggered",
            message=f"Fallback action triggered: {action_type}",
            error_details={"fallback_action": fallback_action, "context": context}
        )
        return {"action": "notify", "message": "Notification sent"}
    else:
        logger.warning(f"Unknown fallback action type: {action_type}")
        return {"action": "unknown", "type": action_type}

