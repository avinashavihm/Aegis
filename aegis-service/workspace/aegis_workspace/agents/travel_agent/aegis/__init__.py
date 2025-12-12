"""
Aegis: Simplified LLM Agent Framework

A comprehensive framework for building LLM-powered agents with:
- Multi-agent orchestration
- Conversational capabilities
- Autonomous operations
- Knowledge grounding
- Agent Store with templates
- Superior Agent Generation 
- Sandbox Execution
- Package Downloads
"""

# Allow imports as both `src.aegis` and `aegis`
import sys as _sys
_sys.modules.setdefault("aegis", _sys.modules[__name__])

from aegis.core import Aegis
from aegis.types import (
    Agent, Response, Result,
    ConversationState, ConversationContext,
    OutputFormat, StructuredInstruction,
    TaskStatus, TaskPlan, SubTask,
    EscalationLevel, EscalationRule,
    AgentCapability
)

# Generator module - Superior agent project generation
from aegis.generator import (
    AgentGenerator,
    AgentSandbox,
    AgentPackager,
    ProjectTemplate,
    AGENT_PROJECT_TYPES
)

__version__ = "0.2.0"

__all__ = [
    # Core
    "Aegis",
    
    # Types
    "Agent",
    "Response", 
    "Result",
    
    # Conversation
    "ConversationState",
    "ConversationContext",
    
    # Instructions
    "OutputFormat",
    "StructuredInstruction",
    
    # Tasks
    "TaskStatus",
    "TaskPlan",
    "SubTask",
    
    # Escalation
    "EscalationLevel",
    "EscalationRule",
    
    # Capabilities
    "AgentCapability",
    
    # Generator (Superior Agent Projects)
    "AgentGenerator",
    "AgentSandbox",
    "AgentPackager",
    "ProjectTemplate",
    "AGENT_PROJECT_TYPES"
]
