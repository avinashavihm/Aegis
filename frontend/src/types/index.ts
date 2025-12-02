export interface Workflow {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowCreate {
  name: string;
  description: string;
}

export interface WorkflowUpdate {
  name?: string;
  description?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface Agent {
  id: string;
  workflow_id: string;
  name: string;
  role: 'planner' | 'retriever' | 'evaluator' | 'executor';
  agent_properties?: Record<string, any>;
  agent_capabilities?: string[];
  agent_status: 'active' | 'inactive' | 'maintenance';
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  role: 'planner' | 'retriever' | 'evaluator' | 'executor';
  agent_properties?: Record<string, any>;
  agent_capabilities?: string[];
  agent_status?: 'active' | 'inactive' | 'maintenance';
}

export interface AgentUpdate {
  name?: string;
  role?: 'planner' | 'retriever' | 'evaluator' | 'executor';
  agent_properties?: Record<string, any>;
  agent_capabilities?: string[];
  agent_status?: 'active' | 'inactive' | 'maintenance';
}

export interface Dependency {
  id: string;
  workflow_id: string;
  agent_id: string;
  depends_on_agent_id: string;
}

export interface DependencyCreate {
  agent_id: string;
  depends_on_agent_id: string;
}

// Execution types
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: ExecutionStatus;
  started_at?: string;
  completed_at?: string;
  logs?: string;
  created_at: string;
  updated_at: string;
}

export interface AgentExecution {
  id: string;
  execution_id: string;
  agent_id: string;
  status: ExecutionStatus;
  started_at?: string;
  completed_at?: string;
  output?: string;
  created_at: string;
  updated_at: string;
}

export interface ExecutionDetail {
  execution: WorkflowExecution;
  agent_executions: AgentExecution[];
}

// Template types
export interface WorkflowTemplate {
  id: string;
  name: string;
  description?: string;
  template_data: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTemplateCreate {
  name: string;
  description?: string;
  template_data: Record<string, any>;
}

export interface WorkflowTemplateUpdate {
  name?: string;
  description?: string;
  template_data?: Record<string, any>;
}

