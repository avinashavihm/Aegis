"""
Escalation Manager for autonomous agents

Handles escalation of tasks to expert agents or human review
when autonomous agents encounter issues or decisions beyond their scope.
"""

import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum

from aegis.types import EscalationLevel, EscalationRule
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


class EscalationStatus(str, Enum):
    """Status of an escalation"""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Escalation:
    """An escalation record"""
    escalation_id: str
    source_agent: str
    target_agent: Optional[str]
    level: EscalationLevel
    reason: str
    context: Dict[str, Any]
    status: EscalationStatus = EscalationStatus.PENDING
    requires_human: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EscalationManager:
    """
    Manages escalations from autonomous agents.
    Supports routing to expert agents and human review.
    """
    
    def __init__(self):
        self.escalations: Dict[str, Escalation] = {}
        self.rules: Dict[str, EscalationRule] = {}
        self.handlers: Dict[EscalationLevel, List[Callable]] = {
            EscalationLevel.LOW: [],
            EscalationLevel.MEDIUM: [],
            EscalationLevel.HIGH: [],
            EscalationLevel.CRITICAL: []
        }
        self.expert_agents: Dict[str, List[str]] = {}  # domain -> list of agent names
        self.human_reviewers: List[str] = []
        self.escalation_history: List[Dict[str, Any]] = []
    
    def register_rule(self, rule: EscalationRule):
        """
        Register an escalation rule.
        
        Args:
            rule: The escalation rule to register
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered escalation rule: {rule.rule_id}", title="EscalationManager")
    
    def register_expert_agent(self, domain: str, agent_name: str):
        """
        Register an expert agent for a domain.
        
        Args:
            domain: The expertise domain
            agent_name: Name of the expert agent
        """
        if domain not in self.expert_agents:
            self.expert_agents[domain] = []
        
        if agent_name not in self.expert_agents[domain]:
            self.expert_agents[domain].append(agent_name)
    
    def register_handler(self, level: EscalationLevel, handler: Callable):
        """
        Register a handler for escalations at a specific level.
        
        Args:
            level: The escalation level
            handler: Handler function
        """
        self.handlers[level].append(handler)
    
    def check_escalation_needed(self, agent_name: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if escalation is needed based on registered rules.
        
        Args:
            agent_name: Name of the agent
            context: Current execution context
            
        Returns:
            Dictionary with escalation details if needed, None otherwise
        """
        for rule in self.rules.values():
            if self._evaluate_condition(rule.condition, context):
                return {
                    "rule_id": rule.rule_id,
                    "level": rule.level.value,
                    "target_agent": rule.target_agent,
                    "requires_human": rule.requires_human,
                    "message": self._render_message(rule.message_template, context)
                }
        
        # Check automatic escalation triggers
        auto_escalation = self._check_auto_triggers(context)
        if auto_escalation:
            return auto_escalation
        
        return None
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate an escalation condition"""
        # Simple condition evaluation
        condition_lower = condition.lower()
        
        # Check for error conditions
        if "error" in condition_lower:
            if context.get("error") or context.get("has_error"):
                return True
        
        # Check for retry exhaustion
        if "retry" in condition_lower or "attempts" in condition_lower:
            retry_count = context.get("retry_count", 0)
            max_retries = context.get("max_retries", 3)
            if retry_count >= max_retries:
                return True
        
        # Check for confidence threshold
        if "confidence" in condition_lower or "uncertain" in condition_lower:
            confidence = context.get("confidence", 1.0)
            if confidence < 0.5:
                return True
        
        # Check for explicit escalation request
        if context.get("escalate") or context.get("needs_escalation"):
            return True
        
        return False
    
    def _check_auto_triggers(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check automatic escalation triggers"""
        # Repeated failures
        failure_count = context.get("failure_count", 0)
        if failure_count >= 3:
            return {
                "rule_id": "auto_repeated_failure",
                "level": EscalationLevel.MEDIUM.value,
                "target_agent": None,
                "requires_human": False,
                "message": f"Task has failed {failure_count} times"
            }
        
        # Critical error
        error = context.get("error", "")
        if any(kw in str(error).lower() for kw in ["critical", "fatal", "security", "unauthorized"]):
            return {
                "rule_id": "auto_critical_error",
                "level": EscalationLevel.CRITICAL.value,
                "target_agent": None,
                "requires_human": True,
                "message": f"Critical error detected: {error}"
            }
        
        # Resource exhaustion
        if context.get("resource_exhausted") or context.get("rate_limited"):
            return {
                "rule_id": "auto_resource_exhaustion",
                "level": EscalationLevel.HIGH.value,
                "target_agent": None,
                "requires_human": False,
                "message": "Resource exhaustion or rate limiting detected"
            }
        
        return None
    
    def _render_message(self, template: str, context: Dict[str, Any]) -> str:
        """Render an escalation message template"""
        message = template
        for key, value in context.items():
            message = message.replace(f"{{{key}}}", str(value))
        return message
    
    def create_escalation(self, source_agent: str, reason: str, context: Dict[str, Any],
                          level: EscalationLevel = EscalationLevel.MEDIUM,
                          target_agent: str = None, requires_human: bool = False) -> Escalation:
        """
        Create a new escalation.
        
        Args:
            source_agent: Agent creating the escalation
            reason: Reason for escalation
            context: Execution context
            level: Escalation level
            target_agent: Specific target agent (optional)
            requires_human: Whether human review is required
            
        Returns:
            Created Escalation
        """
        escalation_id = str(uuid.uuid4())[:8]
        
        escalation = Escalation(
            escalation_id=escalation_id,
            source_agent=source_agent,
            target_agent=target_agent,
            level=level,
            reason=reason,
            context=context,
            requires_human=requires_human
        )
        
        self.escalations[escalation_id] = escalation
        
        # Trigger handlers
        self._trigger_handlers(escalation)
        
        # Record in history
        self.escalation_history.append({
            "escalation_id": escalation_id,
            "source_agent": source_agent,
            "level": level.value,
            "created_at": escalation.created_at
        })
        
        logger.info(
            f"Created escalation {escalation_id} from {source_agent}: {reason}",
            title="Escalation"
        )
        
        return escalation
    
    def _trigger_handlers(self, escalation: Escalation):
        """Trigger registered handlers for an escalation"""
        for handler in self.handlers.get(escalation.level, []):
            try:
                handler(escalation)
            except Exception as e:
                logger.warning(f"Escalation handler error: {e}", title="EscalationManager")
    
    def acknowledge_escalation(self, escalation_id: str, acknowledger: str) -> bool:
        """
        Acknowledge an escalation.
        
        Args:
            escalation_id: The escalation ID
            acknowledger: Who acknowledged the escalation
            
        Returns:
            True if successful
        """
        if escalation_id not in self.escalations:
            return False
        
        escalation = self.escalations[escalation_id]
        escalation.status = EscalationStatus.ACKNOWLEDGED
        escalation.acknowledged_at = datetime.now().isoformat()
        escalation.metadata["acknowledged_by"] = acknowledger
        
        return True
    
    def resolve_escalation(self, escalation_id: str, resolution: str, 
                           resolver: str = None) -> bool:
        """
        Resolve an escalation.
        
        Args:
            escalation_id: The escalation ID
            resolution: Resolution description
            resolver: Who resolved the escalation
            
        Returns:
            True if successful
        """
        if escalation_id not in self.escalations:
            return False
        
        escalation = self.escalations[escalation_id]
        escalation.status = EscalationStatus.RESOLVED
        escalation.resolved_at = datetime.now().isoformat()
        escalation.resolution = resolution
        if resolver:
            escalation.metadata["resolved_by"] = resolver
        
        logger.info(f"Resolved escalation {escalation_id}: {resolution}", title="Escalation")
        
        return True
    
    def cancel_escalation(self, escalation_id: str, reason: str = None) -> bool:
        """
        Cancel an escalation.
        
        Args:
            escalation_id: The escalation ID
            reason: Cancellation reason
            
        Returns:
            True if successful
        """
        if escalation_id not in self.escalations:
            return False
        
        escalation = self.escalations[escalation_id]
        escalation.status = EscalationStatus.CANCELLED
        if reason:
            escalation.metadata["cancellation_reason"] = reason
        
        return True
    
    def get_escalation(self, escalation_id: str) -> Optional[Escalation]:
        """Get an escalation by ID"""
        return self.escalations.get(escalation_id)
    
    def get_pending_escalations(self, level: EscalationLevel = None,
                                 requires_human: bool = None) -> List[Escalation]:
        """
        Get pending escalations with optional filters.
        
        Args:
            level: Filter by level
            requires_human: Filter by human requirement
            
        Returns:
            List of pending escalations
        """
        pending = [
            e for e in self.escalations.values()
            if e.status in [EscalationStatus.PENDING, EscalationStatus.ACKNOWLEDGED]
        ]
        
        if level:
            pending = [e for e in pending if e.level == level]
        
        if requires_human is not None:
            pending = [e for e in pending if e.requires_human == requires_human]
        
        return sorted(pending, key=lambda e: e.created_at)
    
    def get_expert_for_domain(self, domain: str) -> Optional[str]:
        """
        Get an expert agent for a domain.
        
        Args:
            domain: The expertise domain
            
        Returns:
            Agent name or None
        """
        experts = self.expert_agents.get(domain, [])
        if experts:
            return experts[0]  # Return first available expert
        return None
    
    def route_escalation(self, escalation: Escalation) -> Optional[str]:
        """
        Route an escalation to an appropriate handler.
        
        Args:
            escalation: The escalation to route
            
        Returns:
            Name of assigned handler/agent
        """
        # If target agent specified, use it
        if escalation.target_agent:
            return escalation.target_agent
        
        # If requires human, return human indicator
        if escalation.requires_human:
            if self.human_reviewers:
                return f"human:{self.human_reviewers[0]}"
            return "human:unassigned"
        
        # Try to find expert based on context
        context = escalation.context
        task_type = context.get("task_type", "")
        
        # Map task types to domains
        domain_mapping = {
            "file_operation": "file_operations",
            "web_operation": "web",
            "code_execution": "code",
            "analysis": "analysis"
        }
        
        domain = domain_mapping.get(task_type, "general")
        expert = self.get_expert_for_domain(domain)
        
        if expert:
            escalation.target_agent = expert
            return expert
        
        # Fall back to general experts
        general_expert = self.get_expert_for_domain("general")
        if general_expert:
            escalation.target_agent = general_expert
            return general_expert
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get escalation statistics"""
        if not self.escalations:
            return {"total": 0}
        
        by_status = {}
        by_level = {}
        
        for escalation in self.escalations.values():
            status = escalation.status.value
            by_status[status] = by_status.get(status, 0) + 1
            
            level = escalation.level.value
            by_level[level] = by_level.get(level, 0) + 1
        
        # Calculate resolution time for resolved escalations
        resolution_times = []
        for escalation in self.escalations.values():
            if escalation.status == EscalationStatus.RESOLVED and escalation.resolved_at:
                created = datetime.fromisoformat(escalation.created_at)
                resolved = datetime.fromisoformat(escalation.resolved_at)
                resolution_times.append((resolved - created).total_seconds())
        
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        return {
            "total": len(self.escalations),
            "by_status": by_status,
            "by_level": by_level,
            "pending_count": by_status.get("pending", 0) + by_status.get("acknowledged", 0),
            "human_required": sum(1 for e in self.escalations.values() if e.requires_human),
            "avg_resolution_time_seconds": avg_resolution_time,
            "registered_rules": len(self.rules),
            "expert_domains": list(self.expert_agents.keys())
        }
    
    def cleanup_old_escalations(self, max_age_hours: int = 24):
        """Clean up old resolved/cancelled escalations"""
        current_time = datetime.now()
        to_remove = []
        
        for esc_id, escalation in self.escalations.items():
            if escalation.status in [EscalationStatus.RESOLVED, EscalationStatus.CANCELLED]:
                created = datetime.fromisoformat(escalation.created_at)
                age_hours = (current_time - created).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(esc_id)
        
        for esc_id in to_remove:
            del self.escalations[esc_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old escalations", title="EscalationManager")


# Global escalation manager instance
escalation_manager = EscalationManager()

# Register some default rules
escalation_manager.register_rule(EscalationRule(
    rule_id="retry_exhausted",
    condition="retry_count >= max_retries",
    level=EscalationLevel.MEDIUM,
    message_template="Task exhausted all retry attempts: {task}"
))

escalation_manager.register_rule(EscalationRule(
    rule_id="low_confidence",
    condition="confidence < 0.5",
    level=EscalationLevel.LOW,
    message_template="Agent confidence is low ({confidence}): {reason}"
))

escalation_manager.register_rule(EscalationRule(
    rule_id="security_concern",
    condition="security_issue",
    level=EscalationLevel.CRITICAL,
    requires_human=True,
    message_template="Security concern detected: {security_issue}"
))

