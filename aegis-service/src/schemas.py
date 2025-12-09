"""
Pydantic schemas for Aegis agents, workflows, and runs.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from uuid import UUID


# Enums
class AgentStatus(str, Enum):
    """Agent status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class WorkflowStatus(str, Enum):
    """Workflow status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"


class RunStatus(str, Enum):
    """Agent/Workflow run status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(str, Enum):
    """Workflow execution mode"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


# Agent Schemas
class ToolConfig(BaseModel):
    """Configuration for a tool that an agent can use"""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = {}


class AgentCapabilitySchema(BaseModel):
    """Agent capability definition"""
    name: str
    description: str
    keywords: List[str] = []
    priority: int = 0


class AgentCreate(BaseModel):
    """Schema for creating an agent"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    model: str = Field(default="gemini/gemini-2.0-flash")
    instructions: str = Field(default="You are a helpful agent.")
    tools: List[str] = Field(default_factory=list)  # List of tool names
    custom_tool_ids: List[str] = Field(default_factory=list)
    mcp_server_ids: List[str] = Field(default_factory=list)
    file_ids: List[str] = Field(default_factory=list)
    tool_choice: Optional[str] = "auto"
    parallel_tool_calls: bool = True
    capabilities: List[AgentCapabilitySchema] = []
    autonomous_mode: bool = True
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    status: AgentStatus = AgentStatus.ACTIVE


class AgentUpdate(BaseModel):
    """Schema for updating an agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    model: Optional[str] = None
    instructions: Optional[str] = None
    tools: Optional[List[str]] = None
    custom_tool_ids: Optional[List[str]] = None
    mcp_server_ids: Optional[List[str]] = None
    file_ids: Optional[List[str]] = None
    tool_choice: Optional[str] = None
    parallel_tool_calls: Optional[bool] = None
    capabilities: Optional[List[AgentCapabilitySchema]] = None
    autonomous_mode: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[AgentStatus] = None


class AgentResponse(BaseModel):
    """Schema for agent response"""
    id: UUID
    name: str
    description: Optional[str]
    model: str
    instructions: str
    tools: List[str]
    custom_tool_ids: List[str] = []
    mcp_server_ids: List[str] = []
    file_ids: List[str] = []
    tool_choice: Optional[str]
    parallel_tool_calls: bool
    capabilities: List[AgentCapabilitySchema]
    autonomous_mode: bool
    tags: List[str]
    metadata: Dict[str, Any]
    status: AgentStatus
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Workflow Schemas
class WorkflowStep(BaseModel):
    """A step in a workflow"""
    step_id: str
    agent_id: str  # UUID as string
    name: str
    description: Optional[str] = None
    input_mapping: Dict[str, str] = {}  # Map input fields from previous steps
    output_key: Optional[str] = None  # Key to store output for later steps
    config: Dict[str, Any] = {}


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    steps: List[WorkflowStep] = Field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    status: WorkflowStatus = WorkflowStatus.DRAFT


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    steps: Optional[List[WorkflowStep]] = None
    execution_mode: Optional[ExecutionMode] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[WorkflowStatus] = None


class WorkflowResponse(BaseModel):
    """Schema for workflow response"""
    id: UUID
    name: str
    description: Optional[str]
    steps: List[WorkflowStep]
    execution_mode: ExecutionMode
    tags: List[str]
    metadata: Dict[str, Any]
    status: WorkflowStatus
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Run Schemas
class RunCreate(BaseModel):
    """Schema for creating a run (agent or workflow execution)"""
    input_message: str = Field(..., min_length=1)
    context_variables: Dict[str, Any] = {}
    model_override: Optional[str] = None
    max_turns: int = Field(default=10, ge=1, le=50)


class StepResult(BaseModel):
    """Result of a workflow step"""
    step_id: str
    status: RunStatus
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RunResponse(BaseModel):
    """Schema for run response"""
    id: UUID
    run_type: str  # 'agent' or 'workflow'
    agent_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    status: RunStatus
    input_message: str
    context_variables: Dict[str, Any]
    output: Optional[str] = None
    error: Optional[str] = None
    step_results: List[StepResult] = []
    messages: List[Dict[str, Any]] = []  # Conversation history
    tool_calls: List[Dict[str, Any]] = []  # Tool call log
    tokens_used: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class RunListResponse(BaseModel):
    """Schema for listing runs"""
    id: UUID
    run_type: str
    agent_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    status: RunStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# Tool Schemas
class AvailableToolResponse(BaseModel):
    """Schema for available tool info"""
    name: str
    description: Optional[str]
    parameters: List[Any] = []
    category: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = {}


class AvailableToolsResponse(BaseModel):
    """Schema for listing available tools"""
    tools: List[AvailableToolResponse]
    categories: List[str]


# Custom Tool Schemas
class CustomToolCreate(BaseModel):
    name: str
    description: Optional[str] = None
    definition_type: str
    definition: Optional[Dict[str, Any]] = None
    code_content: Optional[str] = None
    parameters: List[Dict[str, Any]] = []
    return_type: str = "any"
    config: Dict[str, Any] = {}


class CustomToolResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    definition_type: str
    parameters: List[Any] = []
    return_type: Optional[str] = None
    is_enabled: bool
    owner_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# MCP Schemas
class MCPServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    server_type: str = "external"
    transport_type: str = "stdio"
    endpoint_url: Optional[str] = None
    command: Optional[str] = None
    args: List[Any] = []
    env_vars: Dict[str, Any] = {}
    config: Dict[str, Any] = {}


class MCPServerResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    server_type: str
    transport_type: str
    endpoint_url: Optional[str]
    status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Agent File Schemas
class AgentFileResponse(BaseModel):
    id: UUID
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    uploaded_at: datetime
    metadata: Dict[str, Any] = {}
