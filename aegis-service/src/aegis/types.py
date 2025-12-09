"""
Core type definitions for Aegis
"""

from typing import List, Callable, Union, Optional, Dict, Any
from pydantic import BaseModel, Field
from litellm.types.utils import ChatCompletionMessageToolCall, Function, Message
from datetime import datetime
from enum import Enum

AgentFunction = Callable[[], Union[str, "Agent", dict]]


class ConversationState(str, Enum):
    """States for conversation flow management"""
    IDLE = "idle"
    AWAITING_INPUT = "awaiting_input"
    PROCESSING = "processing"
    CLARIFYING = "clarifying"
    COMPLETED = "completed"
    ERROR = "error"


class OutputFormat(str, Enum):
    """Supported output formats for structured instructions"""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    TABLE = "table"
    CODE = "code"
    HTML = "html"


class EscalationLevel(str, Enum):
    """Escalation levels for autonomous agents"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


class ConversationContext(BaseModel):
    """Context for managing conversation state and history"""
    session_id: str = ""
    state: ConversationState = ConversationState.IDLE
    turn_count: int = 0
    user_preferences: Dict[str, Any] = {}
    clarification_requests: List[str] = []
    pending_questions: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    def update_state(self, new_state: ConversationState):
        """Update conversation state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now().isoformat()
    
    def increment_turn(self):
        """Increment turn count"""
        self.turn_count += 1
        self.updated_at = datetime.now().isoformat()


class StructuredInstruction(BaseModel):
    """Structured instruction configuration for agents"""
    base_prompt: str = ""
    formatting_rules: Dict[str, str] = {}
    output_format: OutputFormat = OutputFormat.TEXT
    output_schema: Optional[Dict[str, Any]] = None
    constraints: List[str] = []
    examples: List[Dict[str, str]] = []
    variables: Dict[str, Any] = {}
    
    def render(self, context: Dict[str, Any] = None) -> str:
        """Render the instruction with context variables"""
        context = context or {}
        merged_vars = {**self.variables, **context}
        
        rendered = self.base_prompt
        for key, value in merged_vars.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))
        
        # Add formatting rules
        if self.formatting_rules:
            rendered += "\n\nFORMATTING RULES:"
            for rule_name, rule_desc in self.formatting_rules.items():
                rendered += f"\n- {rule_name}: {rule_desc}"
        
        # Add constraints
        if self.constraints:
            rendered += "\n\nCONSTRAINTS:"
            for constraint in self.constraints:
                rendered += f"\n- {constraint}"
        
        # Add output format instruction
        if self.output_format != OutputFormat.TEXT:
            rendered += f"\n\nOUTPUT FORMAT: Respond in {self.output_format.value} format."
            if self.output_schema:
                rendered += f"\nSchema: {self.output_schema}"
        
        return rendered


class TaskPlan(BaseModel):
    """Plan for autonomous task execution"""
    task_id: str = ""
    description: str = ""
    subtasks: List["SubTask"] = []
    dependencies: Dict[str, List[str]] = {}
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SubTask(BaseModel):
    """A subtask within a task plan"""
    subtask_id: str = ""
    parent_task_id: str = ""
    description: str = ""
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class EscalationRule(BaseModel):
    """Rule for determining when to escalate"""
    rule_id: str = ""
    condition: str = ""
    level: EscalationLevel = EscalationLevel.MEDIUM
    target_agent: Optional[str] = None
    requires_human: bool = False
    message_template: str = ""


class AgentCapability(BaseModel):
    """Describes an agent's capabilities for routing"""
    name: str
    description: str
    keywords: List[str] = []
    priority: int = 0
    max_concurrent_tasks: int = 5
    average_response_time: float = 0.0
    success_rate: float = 1.0


class Agent(BaseModel):
    """Agent definition with instructions, model, and tools"""
    name: str = "Agent"
    model: str = "gpt-4o"
    instructions: Union[str, Callable[[dict], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    tool_choice: Optional[str] = None
    parallel_tool_calls: bool = False
    examples: Union[List, Callable[[dict], List]] = []
    handle_mm_func: Optional[Callable] = None
    agent_teams: dict = {}
    
    # Enhanced fields for new features
    structured_instructions: Optional[StructuredInstruction] = None
    capabilities: List[AgentCapability] = []
    escalation_rules: List[EscalationRule] = []
    conversation_context: Optional[ConversationContext] = None
    autonomous_mode: bool = False
    learning_enabled: bool = False
    metadata: Dict[str, Any] = {}
    version: str = "1.0.0"
    tags: List[str] = []
    
    def get_instructions(self, context_variables: dict = None) -> str:
        """Get rendered instructions, supporting both legacy and structured formats"""
        context_variables = context_variables or {}
        
        # If structured instructions are provided, use them
        if self.structured_instructions:
            return self.structured_instructions.render(context_variables)
        
        # Otherwise, use legacy instructions
        if callable(self.instructions):
            return self.instructions(context_variables)
        return self.instructions
    
    def has_capability(self, keyword: str) -> bool:
        """Check if agent has a specific capability"""
        for cap in self.capabilities:
            if keyword.lower() in [k.lower() for k in cap.keywords]:
                return True
        return False


class Response(BaseModel):
    """Response from agent execution"""
    messages: List = []
    agent: Optional[Agent] = None
    context_variables: dict = {}
    conversation_context: Optional[ConversationContext] = None
    task_status: Optional[TaskStatus] = None
    escalation: Optional[Dict[str, Any]] = None


class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.
    
    Attributes:
        value: The result value as a string
        agent: The agent instance, if applicable
        context_variables: A dictionary of context variables
        image: Base64 encoded image, if applicable
    """
    value: str = ""
    agent: Optional[Agent] = None
    context_variables: dict = {}
    image: Optional[str] = None  # base64 encoded image
    task_status: Optional[TaskStatus] = None
    needs_escalation: bool = False
    escalation_reason: Optional[str] = None


# Update forward references
TaskPlan.model_rebuild()
