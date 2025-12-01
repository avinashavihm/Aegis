from pydantic import BaseModel, field_validator, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# Role enum for validation
class AgentRole(str, Enum):
    """Valid agent roles"""
    PLANNER = "planner"
    RETRIEVER = "retriever"
    EVALUATOR = "evaluator"
    EXECUTOR = "executor"


# Workflow Schemas
class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty")
        return v.strip() if v else None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Agent Status enum
class AgentStatus(str, Enum):
    """Agent status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


# Agent Schemas
class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    role: str  # planner, retriever, evaluator, executor
    agent_properties: Optional[Dict[str, Any]] = None
    agent_capabilities: Optional[List[str]] = None
    agent_status: Optional[str] = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        try:
            role = AgentRole(v.lower())
            return role.value
        except ValueError:
            valid_roles = [r.value for r in AgentRole]
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
    
    @field_validator("agent_status")
    @classmethod
    def validate_agent_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            status = AgentStatus(v.lower())
            return status.value
        except ValueError:
            valid_statuses = [s.value for s in AgentStatus]
            raise ValueError(f"Agent status must be one of: {', '.join(valid_statuses)}")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    role: Optional[str] = None
    agent_properties: Optional[Dict[str, Any]] = None
    agent_capabilities: Optional[List[str]] = None
    agent_status: Optional[str] = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty")
        return v.strip() if v else None
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            role = AgentRole(v.lower())
            return role.value
        except ValueError:
            valid_roles = [r.value for r in AgentRole]
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
    
    @field_validator("agent_status")
    @classmethod
    def validate_agent_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            status = AgentStatus(v.lower())
            return status.value
        except ValueError:
            valid_statuses = [s.value for s in AgentStatus]
            raise ValueError(f"Agent status must be one of: {', '.join(valid_statuses)}")


class AgentResponse(BaseModel):
    id: str
    workflow_id: str
    name: str
    role: str
    agent_properties: Optional[Dict[str, Any]] = None
    agent_capabilities: Optional[List[str]] = None
    agent_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Dependency Schemas
class DependencyCreate(BaseModel):
    agent_id: str = Field(..., min_length=1)
    depends_on_agent_id: str = Field(..., min_length=1)
    
    @field_validator("agent_id", "depends_on_agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Agent ID cannot be empty")
        return v.strip()


class DependencyResponse(BaseModel):
    id: str
    workflow_id: str
    agent_id: str
    depends_on_agent_id: str
    
    class Config:
        from_attributes = True


# Request/Response for bulk operations
class AgentsUpdateRequest(BaseModel):
    agents: List[AgentCreate] = Field(..., min_items=0)


class DependenciesUpdateRequest(BaseModel):
    dependencies: List[DependencyCreate] = Field(..., min_items=0)


# Pagination schemas
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)


class WorkflowListResponse(BaseModel):
    items: List[WorkflowResponse]
    total: int
    page: int
    limit: int
    pages: int


# Execution Status enum
class ExecutionStatus(str, Enum):
    """Execution status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Execution Schemas
class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    logs: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AgentExecutionResponse(BaseModel):
    id: str
    execution_id: str
    agent_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExecutionDetailResponse(BaseModel):
    """Detailed execution response with agent executions"""
    execution: WorkflowExecutionResponse
    agent_executions: List[AgentExecutionResponse]


# Template Schemas
class WorkflowTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    template_data: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class WorkflowTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty")
        return v.strip() if v else None


class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    template_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TemplateApplyRequest(BaseModel):
    """Request to apply a template to create a workflow"""
    template_id: str
    workflow_name: str = Field(..., min_length=1, max_length=200)
    workflow_description: Optional[str] = None
    overrides: Optional[Dict[str, Any]] = None

