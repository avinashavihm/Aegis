from sqlmodel import SQLModel, Field, Relationship, Column, DateTime, Index
from sqlalchemy import JSON, Text
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from enum import Enum


class Workflow(SQLModel, table=True):
    """Workflow model"""
    __tablename__ = "workflow"
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    description: str
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    
    # Relationships with cascade delete
    agents: List["Agent"] = Relationship(
        back_populates="workflow",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    dependencies: List["AgentDependency"] = Relationship(
        back_populates="workflow",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_workflow_created_at", "created_at"),
        Index("idx_workflow_deleted_at", "deleted_at"),
    )


class AgentStatus(str, Enum):
    """Agent status enum"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class CapabilityType(str, Enum):
    """Agent capability type enum"""
    DATA_PROCESSING = "data_processing"
    API_INTEGRATION = "api_integration"
    FILE_OPERATIONS = "file_operations"
    DATABASE_OPERATIONS = "database_operations"
    ML_AI = "ml_ai"
    WEB_SCRAPING = "web_scraping"
    COMMUNICATION = "communication"
    SCHEDULING = "scheduling"
    MONITORING = "monitoring"
    SECURITY = "security"
    CUSTOM = "custom"


class Agent(SQLModel, table=True):
    """Agent model"""
    __tablename__ = "agent"
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    workflow_id: str = Field(foreign_key="workflow.id", index=True)
    name: str
    role: str  # planner, retriever, evaluator, executor
    agent_properties: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    agent_capabilities: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    capability_config: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    resource_limits: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    agent_status: str = Field(
        default=AgentStatus.ACTIVE.value,
        sa_column=Column(Text, default=AgentStatus.ACTIVE.value)
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    
    # Relationships
    workflow: Optional[Workflow] = Relationship(back_populates="agents")
    
    # Indexes
    __table_args__ = (
        Index("idx_agent_workflow_id", "workflow_id"),
        Index("idx_agent_role", "role"),
        Index("idx_agent_deleted_at", "deleted_at"),
        Index("idx_agent_status", "agent_status"),
    )


class AgentDependency(SQLModel, table=True):
    """Agent dependency model for DAG structure"""
    __tablename__ = "agent_dependency"
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    workflow_id: str = Field(foreign_key="workflow.id", index=True)
    agent_id: str = Field(foreign_key="agent.id", index=True)
    depends_on_agent_id: str = Field(foreign_key="agent.id", index=True)
    
    # Relationships
    workflow: Optional[Workflow] = Relationship(back_populates="dependencies")
    
    # Indexes
    __table_args__ = (
        Index("idx_dependency_workflow_id", "workflow_id"),
        Index("idx_dependency_agent_id", "agent_id"),
        Index("idx_dependency_depends_on", "depends_on_agent_id"),
        Index("idx_dependency_unique", "workflow_id", "agent_id", "depends_on_agent_id", unique=True),
    )


class ExecutionStatus(str, Enum):
    """Execution status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ExecutionMode(str, Enum):
    """Execution mode enum"""
    SYNC = "sync"
    ASYNC = "async"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"


class WorkflowExecution(SQLModel, table=True):
    """Workflow execution model"""
    __tablename__ = "workflow_execution"
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    workflow_id: str = Field(foreign_key="workflow.id", index=True)
    status: str = Field(
        default=ExecutionStatus.PENDING.value,
        sa_column=Column(Text, default=ExecutionStatus.PENDING.value)
    )
    execution_mode: str = Field(
        default=ExecutionMode.SYNC.value,
        sa_column=Column(Text, default=ExecutionMode.SYNC.value)
    )
    execution_context: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    priority: int = Field(default=0, description="Execution priority (higher = more priority)")
    started_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    logs: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    error_details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # Relationships
    agent_executions: List["AgentExecution"] = Relationship(
        back_populates="workflow_execution",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_workflow_execution_workflow_id", "workflow_id"),
        Index("idx_workflow_execution_status", "status"),
        Index("idx_workflow_execution_started_at", "started_at"),
        Index("idx_workflow_execution_priority", "priority"),
        Index("idx_workflow_execution_mode", "execution_mode"),
    )


class AgentExecution(SQLModel, table=True):
    """Agent execution model"""
    __tablename__ = "agent_execution"
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    execution_id: str = Field(foreign_key="workflow_execution.id", index=True)
    agent_id: str = Field(foreign_key="agent.id", index=True)
    status: str = Field(
        default=ExecutionStatus.PENDING.value,
        sa_column=Column(Text, default=ExecutionStatus.PENDING.value)
    )
    started_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=True)
    )
    output: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    retry_count: int = Field(default=0)
    duration_ms: Optional[int] = Field(default=None)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # Relationships
    workflow_execution: Optional[WorkflowExecution] = Relationship(back_populates="agent_executions")
    
    # Indexes
    __table_args__ = (
        Index("idx_agent_execution_execution_id", "execution_id"),
        Index("idx_agent_execution_agent_id", "agent_id"),
        Index("idx_agent_execution_status", "status"),
    )


class WorkflowTemplate(SQLModel, table=True):
    """Workflow template model"""
    __tablename__ = "workflow_template"
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True)
    )
    template_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_workflow_template_name", "name"),
        Index("idx_workflow_template_created_at", "created_at"),
    )

