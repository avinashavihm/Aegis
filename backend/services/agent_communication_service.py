"""Service for agent communication and collaboration"""
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class MessageBus:
    """Message bus for inter-agent communication"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.messages: List[Dict[str, Any]] = []
    
    def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to a topic"""
        self.subscribers[topic].append(callback)
        logger.info(f"Subscribed to topic: {topic}")
    
    def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a message to a topic"""
        message_data = {
            "topic": topic,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.messages.append(message_data)
        
        # Notify subscribers
        for callback in self.subscribers.get(topic, []):
            try:
                callback(message_data)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}", exc_info=True)
    
    def get_messages(self, topic: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages, optionally filtered by topic"""
        messages = self.messages
        if topic:
            messages = [m for m in messages if m.get("topic") == topic]
        return messages[-limit:]


class SharedContext:
    """Shared context for workflow execution"""
    
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.variables: Dict[str, Any] = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable in shared context"""
        self.variables[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable from shared context"""
        return self.variables.get(key, default)
    
    def get_all_variables(self) -> Dict[str, Any]:
        """Get all variables"""
        return self.variables.copy()


class AgentDiscovery:
    """Agent discovery and capability registry"""
    
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.capabilities: Dict[str, List[str]] = defaultdict(list)  # capability -> [agent_ids]
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any]) -> None:
        """Register an agent"""
        self.agents[agent_id] = agent_info
        
        # Index by capabilities
        agent_capabilities = agent_info.get("capabilities", [])
        for capability in agent_capabilities:
            self.capabilities[capability].append(agent_id)
    
    def discover_agents(self, capability: str) -> List[str]:
        """Discover agents with a specific capability"""
        return self.capabilities.get(capability, [])
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information"""
        return self.agents.get(agent_id)


# Global instances
_message_bus = MessageBus()
_shared_contexts: Dict[str, SharedContext] = {}
_agent_discovery = AgentDiscovery()


def get_message_bus() -> MessageBus:
    """Get the global message bus"""
    return _message_bus


def get_shared_context(execution_id: str) -> SharedContext:
    """Get or create shared context for an execution"""
    if execution_id not in _shared_contexts:
        _shared_contexts[execution_id] = SharedContext(execution_id)
    return _shared_contexts[execution_id]


def get_agent_discovery() -> AgentDiscovery:
    """Get the global agent discovery instance"""
    return _agent_discovery

