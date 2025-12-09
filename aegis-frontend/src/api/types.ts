// Auth types
export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
}

// User types
export interface User {
  id: string
  username: string
  email: string
  full_name?: string
  created_at: string
  updated_at: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
  full_name?: string
}

// Team types
export interface Team {
  id: string
  name: string
  owner_id: string
  created_at: string
  updated_at: string
}

export interface TeamCreate {
  name: string
}

export interface TeamMember {
  user_id: string
  role_id?: string
  joined_at: string
}

// Role types
export interface Role {
  id: string
  name: string
  description?: string
  created_at: string
  updated_at: string
}

export interface RoleCreate {
  name: string
  description?: string
}

// Policy types
export interface Policy {
  id: string
  name: string
  description?: string
  content: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface PolicyCreate {
  name: string
  description?: string
  content: Record<string, unknown>
}

// Workspace types
export interface Workspace {
  id: string
  name: string
  description?: string
  owner_id: string
  content: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface WorkspaceCreate {
  name: string
  description?: string
  content?: Record<string, unknown>
}

// Agent types
export interface AgentCapability {
  name: string
  description: string
  keywords: string[]
  priority: number
}

export interface Agent {
  id: string
  name: string
  description?: string
  model: string
  instructions: string
  tools: string[]
  custom_tool_ids: string[]
  mcp_server_ids: string[]
  file_ids: string[]
  tool_choice?: string
  parallel_tool_calls: boolean
  capabilities: AgentCapability[]
  autonomous_mode: boolean
  tags: string[]
  metadata: Record<string, unknown>
  status: string
  owner_id: string
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  name: string
  description?: string
  model?: string
  instructions?: string
  tools?: string[]
  custom_tool_ids?: string[]
  mcp_server_ids?: string[]
  file_ids?: string[]
  tool_choice?: string
  parallel_tool_calls?: boolean
  capabilities?: AgentCapability[]
  autonomous_mode?: boolean
  tags?: string[]
  metadata?: Record<string, unknown>
  status?: string
}

export interface RunRequest {
  input_message: string
  context_variables?: Record<string, unknown>
  model_override?: string
  max_turns?: number
}

// Workflow types
export interface WorkflowStep {
  agent_id?: string
  action: string
  params?: Record<string, unknown>
}

export interface Workflow {
  id: string
  name: string
  description?: string
  steps: WorkflowStep[]
  execution_mode: string
  tags: string[]
  metadata: Record<string, unknown>
  status: string
  owner_id: string
  created_at: string
  updated_at: string
}

export interface WorkflowCreate {
  name: string
  description?: string
  steps?: WorkflowStep[]
  execution_mode?: string
  tags?: string[]
  metadata?: Record<string, unknown>
  status?: string
}

// Run types
export interface Run {
  id: string
  run_type: string
  agent_id?: string
  workflow_id?: string
  status: string
  input_message: string
  context_variables: Record<string, unknown>
  output?: string
  error?: string
  step_results: unknown[]
  messages: unknown[]
  tool_calls: unknown[]
  tokens_used: number
  started_at?: string
  completed_at?: string
  owner_id: string
  created_at: string
}

// Tool registry types
export interface AvailableTool {
  name: string
  description?: string
  parameters: unknown[]
  category: string
  source?: string
  metadata?: Record<string, unknown>
}

export interface ToolListResponse {
  tools: AvailableTool[]
  categories: string[]
}

// Custom tools
export interface CustomToolCreate {
  name: string
  description?: string
  definition_type: string
  definition?: Record<string, unknown>
  code_content?: string
  parameters?: Record<string, unknown>[]
  return_type?: string
  config?: Record<string, unknown>
}

export interface CustomTool {
  id: string
  name: string
  description?: string
  definition_type: string
  parameters?: Record<string, unknown>[]
  return_type?: string
  is_enabled: boolean
  owner_id?: string
  created_at: string
  updated_at?: string
}

// MCP servers
export interface MCPServerCreate {
  name: string
  description?: string
  server_type?: string
  transport_type?: string
  endpoint_url?: string
  command?: string
  args?: unknown[]
  env_vars?: Record<string, unknown>
  config?: Record<string, unknown>
}

export interface MCPServer {
  id: string
  name: string
  description?: string
  server_type: string
  transport_type: string
  endpoint_url?: string
  status?: string
  created_at: string
  updated_at?: string
}

// Agent files
export interface AgentFile {
  id: string
  file_name: string
  file_type?: string
  file_size?: number
  content_type?: string
  uploaded_at: string
  metadata?: Record<string, unknown>
}

// API Keys
export interface APIKey {
  id: string
  name: string
  provider: string
  api_key_preview: string
  base_url?: string
  organization_id?: string
  is_default: boolean
  is_active: boolean
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface APIKeyCreate {
  name: string
  provider: string
  api_key: string
  base_url?: string
  organization_id?: string
  is_default?: boolean
  metadata?: Record<string, unknown>
}

// AI Models
export interface AIModel {
  id: string
  provider: string
  model_id: string
  display_name: string
  description?: string
  capabilities: string[]
  context_window: number
  max_output_tokens?: number
  supports_streaming: boolean
  supports_tools: boolean
  supports_vision: boolean
  is_available: boolean
}

export interface AIProvider {
  id: string
  name: string
  description: string
  requires_key: boolean
  requires_base_url?: boolean
  key_url: string
}

// Agent Topics (Conversation Flows)
export interface AgentTopic {
  id: string
  agent_id: string
  name: string
  description?: string
  trigger_type: string
  trigger_phrases: string[]
  trigger_config: Record<string, unknown>
  conversation_flow: ConversationNode[]
  is_enabled: boolean
  priority: number
  created_at: string
  updated_at: string
}

export interface ConversationNode {
  id: string
  type: 'message' | 'question' | 'condition' | 'action' | 'handoff'
  content?: string
  options?: string[]
  condition?: string
  action_id?: string
  next_nodes?: string[]
}

export interface TopicCreate {
  name: string
  description?: string
  trigger_type?: string
  trigger_phrases?: string[]
  trigger_config?: Record<string, unknown>
  conversation_flow?: ConversationNode[]
  is_enabled?: boolean
  priority?: number
}

// Agent Actions (Connectors)
export interface AgentAction {
  id: string
  agent_id: string
  name: string
  description?: string
  action_type: string
  config: Record<string, unknown>
  input_schema: Record<string, unknown>
  output_schema: Record<string, unknown>
  authentication: Record<string, unknown>
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface ActionCreate {
  name: string
  description?: string
  action_type: string
  config?: Record<string, unknown>
  input_schema?: Record<string, unknown>
  output_schema?: Record<string, unknown>
  authentication?: Record<string, unknown>
  is_enabled?: boolean
}

// Agent Knowledge Base
export interface AgentKnowledge {
  id: string
  agent_id: string
  name: string
  source_type: string
  source_url?: string
  file_type?: string
  file_size?: number
  chunk_count: number
  embedding_status: string
  last_synced_at?: string
  sync_frequency: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface KnowledgeCreate {
  name: string
  source_type: string
  source_url?: string
  content?: string
  sync_frequency?: string
  is_enabled?: boolean
}
