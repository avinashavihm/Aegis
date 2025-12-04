"""
Escalation Tools for autonomous agents
"""

import json
from typing import Optional, Dict, Any

from aegis.registry import register_tool
from aegis.types import EscalationLevel
from aegis.agents.autonomous.escalation_manager import escalation_manager, EscalationStatus


@register_tool("check_escalation_needed")
def check_escalation_needed(agent_name: str, context_variables: dict = None) -> str:
    """
    Check if escalation is needed based on current context.
    
    Args:
        agent_name: Name of the agent checking
        
    Returns:
        JSON string with escalation check result
    """
    context = context_variables or {}
    
    result = escalation_manager.check_escalation_needed(agent_name, context)
    
    if result:
        return json.dumps({
            "status": "escalation_needed",
            "rule_id": result["rule_id"],
            "level": result["level"],
            "target_agent": result["target_agent"],
            "requires_human": result["requires_human"],
            "message": result["message"]
        }, indent=2)
    else:
        return json.dumps({
            "status": "no_escalation",
            "message": "No escalation needed based on current context"
        }, indent=2)


@register_tool("create_escalation")
def create_escalation(reason: str, level: str = "medium",
                      target_agent: str = None, requires_human: bool = False,
                      context_variables: dict = None) -> str:
    """
    Create an escalation to expert agents or human review.
    
    Args:
        reason: Reason for escalation
        level: Escalation level (low, medium, high, critical)
        target_agent: Specific agent to escalate to (optional)
        requires_human: Whether human review is required
        
    Returns:
        JSON string with escalation details
    """
    context = context_variables or {}
    agent_name = context.get("current_agent", "unknown")
    
    # Map level string to enum
    level_map = {
        "low": EscalationLevel.LOW,
        "medium": EscalationLevel.MEDIUM,
        "high": EscalationLevel.HIGH,
        "critical": EscalationLevel.CRITICAL
    }
    escalation_level = level_map.get(level.lower(), EscalationLevel.MEDIUM)
    
    escalation = escalation_manager.create_escalation(
        source_agent=agent_name,
        reason=reason,
        context=context,
        level=escalation_level,
        target_agent=target_agent,
        requires_human=requires_human
    )
    
    # Route the escalation
    assigned_to = escalation_manager.route_escalation(escalation)
    
    return json.dumps({
        "status": "success",
        "escalation_id": escalation.escalation_id,
        "level": escalation.level.value,
        "assigned_to": assigned_to,
        "requires_human": escalation.requires_human,
        "message": f"Escalation created: {reason}"
    }, indent=2)


@register_tool("resolve_escalation")
def resolve_escalation(escalation_id: str, resolution: str,
                       context_variables: dict = None) -> str:
    """
    Resolve an existing escalation.
    
    Args:
        escalation_id: ID of the escalation to resolve
        resolution: Description of how it was resolved
        
    Returns:
        JSON string with resolution status
    """
    context = context_variables or {}
    resolver = context.get("current_agent", "unknown")
    
    success = escalation_manager.resolve_escalation(escalation_id, resolution, resolver)
    
    if success:
        return json.dumps({
            "status": "success",
            "escalation_id": escalation_id,
            "resolution": resolution,
            "message": "Escalation resolved successfully"
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Escalation {escalation_id} not found"
        }, indent=2)


@register_tool("acknowledge_escalation")
def acknowledge_escalation(escalation_id: str, context_variables: dict = None) -> str:
    """
    Acknowledge an escalation (mark as being worked on).
    
    Args:
        escalation_id: ID of the escalation to acknowledge
        
    Returns:
        JSON string with acknowledgment status
    """
    context = context_variables or {}
    acknowledger = context.get("current_agent", "unknown")
    
    success = escalation_manager.acknowledge_escalation(escalation_id, acknowledger)
    
    if success:
        escalation = escalation_manager.get_escalation(escalation_id)
        return json.dumps({
            "status": "success",
            "escalation_id": escalation_id,
            "source_agent": escalation.source_agent if escalation else None,
            "reason": escalation.reason if escalation else None,
            "message": "Escalation acknowledged"
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Escalation {escalation_id} not found"
        }, indent=2)


@register_tool("list_escalations")
def list_escalations(status_filter: str = None, level_filter: str = None,
                     context_variables: dict = None) -> str:
    """
    List escalations with optional filters.
    
    Args:
        status_filter: Filter by status (pending, acknowledged, resolved, etc.)
        level_filter: Filter by level (low, medium, high, critical)
        
    Returns:
        JSON string with list of escalations
    """
    level_map = {
        "low": EscalationLevel.LOW,
        "medium": EscalationLevel.MEDIUM,
        "high": EscalationLevel.HIGH,
        "critical": EscalationLevel.CRITICAL
    }
    
    level = level_map.get(level_filter.lower()) if level_filter else None
    
    if status_filter and status_filter.lower() in ["pending", "acknowledged"]:
        escalations = escalation_manager.get_pending_escalations(level=level)
    else:
        escalations = list(escalation_manager.escalations.values())
        if level:
            escalations = [e for e in escalations if e.level == level]
        if status_filter:
            escalations = [e for e in escalations if e.status.value == status_filter.lower()]
    
    escalation_list = [
        {
            "escalation_id": e.escalation_id,
            "source_agent": e.source_agent,
            "target_agent": e.target_agent,
            "level": e.level.value,
            "status": e.status.value,
            "reason": e.reason[:100] + "..." if len(e.reason) > 100 else e.reason,
            "requires_human": e.requires_human,
            "created_at": e.created_at
        }
        for e in escalations
    ]
    
    return json.dumps({
        "status": "success",
        "total": len(escalation_list),
        "escalations": escalation_list
    }, indent=2)


@register_tool("get_escalation_details")
def get_escalation_details(escalation_id: str, context_variables: dict = None) -> str:
    """
    Get detailed information about an escalation.
    
    Args:
        escalation_id: ID of the escalation
        
    Returns:
        JSON string with escalation details
    """
    escalation = escalation_manager.get_escalation(escalation_id)
    
    if not escalation:
        return json.dumps({
            "status": "error",
            "message": f"Escalation {escalation_id} not found"
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "escalation": {
            "escalation_id": escalation.escalation_id,
            "source_agent": escalation.source_agent,
            "target_agent": escalation.target_agent,
            "level": escalation.level.value,
            "status": escalation.status.value,
            "reason": escalation.reason,
            "requires_human": escalation.requires_human,
            "context": escalation.context,
            "created_at": escalation.created_at,
            "acknowledged_at": escalation.acknowledged_at,
            "resolved_at": escalation.resolved_at,
            "resolution": escalation.resolution,
            "metadata": escalation.metadata
        }
    }, indent=2)


@register_tool("get_escalation_statistics")
def get_escalation_statistics(context_variables: dict = None) -> str:
    """
    Get statistics about escalations.
    
    Returns:
        JSON string with escalation statistics
    """
    stats = escalation_manager.get_statistics()
    
    return json.dumps({
        "status": "success",
        "statistics": stats
    }, indent=2)


@register_tool("register_expert_agent")
def register_expert_agent(domain: str, agent_name: str, context_variables: dict = None) -> str:
    """
    Register an agent as an expert for a domain.
    
    Args:
        domain: The expertise domain (e.g., "code", "web", "file_operations")
        agent_name: Name of the expert agent
        
    Returns:
        JSON string with registration status
    """
    escalation_manager.register_expert_agent(domain, agent_name)
    
    return json.dumps({
        "status": "success",
        "domain": domain,
        "agent_name": agent_name,
        "message": f"Agent {agent_name} registered as expert for {domain}"
    }, indent=2)

