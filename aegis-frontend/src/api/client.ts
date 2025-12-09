import type {
  LoginResponse, RegisterRequest,
  User, UserCreate,
  Team, TeamCreate,
  Role, RoleCreate,
  Policy, PolicyCreate,
  Workspace, WorkspaceCreate,
  Agent, AgentCreate, RunRequest,
  Workflow, WorkflowCreate,
  Run,
  ToolListResponse, AvailableTool,
  CustomToolCreate, CustomTool,
  MCPServerCreate, MCPServer,
  AgentFile,
  APIKey, APIKeyCreate,
  AIModel, AIProvider,
  AgentTopic, TopicCreate,
  AgentAction, ActionCreate,
  AgentKnowledge, KnowledgeCreate
} from './types'

const API_BASE = 'http://localhost:8000'

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

function getToken(): string | null {
  return localStorage.getItem('aegis_token')
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const isForm = options.body instanceof FormData
  const headers: HeadersInit = {
    ...(!isForm ? { 'Content-Type': 'application/json' } : {}),
    ...options.headers,
  }

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const errorData = await response.json()
      message = errorData.detail || message
    } catch {
      // ignore
    }
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export const api = {
  // Auth
  login: async (username: string, password: string): Promise<LoginResponse> => {
    return request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  },

  register: async (data: RegisterRequest): Promise<User> => {
    return request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  getMe: async (): Promise<User> => {
    return request<User>('/auth/me')
  },

  // Users
  listUsers: async (): Promise<User[]> => {
    return request<User[]>('/users')
  },

  getUser: async (id: string): Promise<User> => {
    return request<User>(`/users/${id}`)
  },

  createUser: async (data: UserCreate): Promise<User> => {
    return request<User>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteUser: async (id: string): Promise<void> => {
    return request<void>(`/users/${id}`, { method: 'DELETE' })
  },

  // Teams
  listTeams: async (): Promise<Team[]> => {
    return request<Team[]>('/teams')
  },

  getTeam: async (id: string): Promise<Team> => {
    return request<Team>(`/teams/${id}`)
  },

  createTeam: async (data: TeamCreate): Promise<Team> => {
    return request<Team>('/teams', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteTeam: async (id: string): Promise<void> => {
    return request<void>(`/teams/${id}`, { method: 'DELETE' })
  },

  addTeamMember: async (teamId: string, userId: string, roleId?: string): Promise<void> => {
    return request<void>(`/teams/${teamId}/members`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, role_id: roleId }),
    })
  },

  removeTeamMember: async (teamId: string, userId: string): Promise<void> => {
    return request<void>(`/teams/${teamId}/members/${userId}`, { method: 'DELETE' })
  },

  // Roles
  listRoles: async (): Promise<Role[]> => {
    return request<Role[]>('/roles')
  },

  getRole: async (id: string): Promise<Role> => {
    return request<Role>(`/roles/${id}`)
  },

  createRole: async (data: RoleCreate): Promise<Role> => {
    return request<Role>('/roles', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteRole: async (id: string): Promise<void> => {
    return request<void>(`/roles/${id}`, { method: 'DELETE' })
  },

  attachPolicyToRole: async (roleId: string, policyId: string): Promise<void> => {
    return request<void>(`/roles/${roleId}/policies/${policyId}`, { method: 'POST' })
  },

  detachPolicyFromRole: async (roleId: string, policyId: string): Promise<void> => {
    return request<void>(`/roles/${roleId}/policies/${policyId}`, { method: 'DELETE' })
  },

  assignRoleToUser: async (userId: string, roleId: string): Promise<void> => {
    return request<void>(`/users/${userId}/roles/${roleId}`, { method: 'POST' })
  },

  removeRoleFromUser: async (userId: string, roleId: string): Promise<void> => {
    return request<void>(`/users/${userId}/roles/${roleId}`, { method: 'DELETE' })
  },

  // Policies
  listPolicies: async (): Promise<Policy[]> => {
    return request<Policy[]>('/policies')
  },

  getPolicy: async (id: string): Promise<Policy> => {
    return request<Policy>(`/policies/${id}`)
  },

  createPolicy: async (data: PolicyCreate): Promise<Policy> => {
    return request<Policy>('/policies', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deletePolicy: async (id: string): Promise<void> => {
    return request<void>(`/policies/${id}`, { method: 'DELETE' })
  },

  // Workspaces
  listWorkspaces: async (): Promise<Workspace[]> => {
    return request<Workspace[]>('/workspaces')
  },

  getWorkspace: async (id: string): Promise<Workspace> => {
    return request<Workspace>(`/workspaces/${id}`)
  },

  createWorkspace: async (data: WorkspaceCreate): Promise<Workspace> => {
    return request<Workspace>('/workspaces', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteWorkspace: async (id: string): Promise<void> => {
    return request<void>(`/workspaces/${id}`, { method: 'DELETE' })
  },

  // Agents
  listAgents: async (): Promise<Agent[]> => {
    return request<Agent[]>('/agents')
  },

  getAgent: async (id: string): Promise<Agent> => {
    return request<Agent>(`/agents/${id}`)
  },

  createAgent: async (data: AgentCreate): Promise<Agent> => {
    return request<Agent>('/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  updateAgent: async (id: string, data: Partial<AgentCreate>): Promise<Agent> => {
    return request<Agent>(`/agents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  deleteAgent: async (id: string): Promise<void> => {
    return request<void>(`/agents/${id}`, { method: 'DELETE' })
  },

  runAgent: async (agentId: string, data: RunRequest): Promise<Run> => {
    return request<Run>(`/agents/${agentId}/run`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  listAgentRuns: async (agentId: string): Promise<Run[]> => {
    return request<Run[]>(`/agents/${agentId}/runs`)
  },

  // Agent files
  uploadAgentFile: async (agentId: string, file: File): Promise<AgentFile> => {
    const form = new FormData()
    form.append('upload', file)
    return request<AgentFile>(`/agents/${agentId}/files`, {
      method: 'POST',
      body: form,
    })
  },

  listAgentFiles: async (agentId: string): Promise<AgentFile[]> => {
    return request<AgentFile[]>(`/agents/${agentId}/files`)
  },

  deleteAgentFile: async (agentId: string, fileId: string): Promise<void> => {
    return request<void>(`/agents/${agentId}/files/${fileId}`, { method: 'DELETE' })
  },

  // Tool registry & custom tools
  listTools: async (): Promise<ToolListResponse> => {
    return request<ToolListResponse>('/tools')
  },

  getTool: async (name: string): Promise<AvailableTool> => {
    return request<AvailableTool>(`/tools/${name}`)
  },

  listCustomTools: async (): Promise<CustomTool[]> => {
    return request<CustomTool[]>('/tools/custom/list')
  },

  createCustomTool: async (tool: CustomToolCreate): Promise<CustomTool> => {
    return request<CustomTool>('/tools/custom', {
      method: 'POST',
      body: JSON.stringify(tool),
    })
  },

  deleteCustomTool: async (toolId: string): Promise<void> => {
    return request<void>(`/tools/custom/${toolId}`, { method: 'DELETE' })
  },

  // MCP servers
  listMCPServers: async (): Promise<MCPServer[]> => {
    return request<MCPServer[]>('/mcp/servers')
  },

  createMCPServer: async (server: MCPServerCreate): Promise<MCPServer> => {
    return request<MCPServer>('/mcp/servers', {
      method: 'POST',
      body: JSON.stringify(server),
    })
  },

  attachMCPServer: async (agentId: string, serverId: string): Promise<void> => {
    return request<void>(`/mcp/agents/${agentId}/${serverId}`, { method: 'POST' })
  },

  detachMCPServer: async (agentId: string, serverId: string): Promise<void> => {
    return request<void>(`/mcp/agents/${agentId}/${serverId}`, { method: 'DELETE' })
  },

  // Workflows
  listWorkflows: async (): Promise<Workflow[]> => {
    return request<Workflow[]>('/workflows')
  },

  getWorkflow: async (id: string): Promise<Workflow> => {
    return request<Workflow>(`/workflows/${id}`)
  },

  createWorkflow: async (data: WorkflowCreate): Promise<Workflow> => {
    return request<Workflow>('/workflows', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteWorkflow: async (id: string): Promise<void> => {
    return request<void>(`/workflows/${id}`, { method: 'DELETE' })
  },

  runWorkflow: async (workflowId: string, data: RunRequest): Promise<Run> => {
    return request<Run>(`/workflows/${workflowId}/run`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  // Runs
  listRuns: async (limit?: number): Promise<Run[]> => {
    const query = limit ? `?limit=${limit}` : ''
    return request<Run[]>(`/runs${query}`)
  },

  getRun: async (id: string): Promise<Run> => {
    return request<Run>(`/runs/${id}`)
  },

  // ============================================
  // SETTINGS - API Keys, Models, etc.
  // ============================================

  // API Keys
  listAPIKeys: async (): Promise<APIKey[]> => {
    return request<APIKey[]>('/settings/api-keys')
  },

  createAPIKey: async (data: APIKeyCreate): Promise<APIKey> => {
    return request<APIKey>('/settings/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  updateAPIKey: async (id: string, data: Partial<APIKeyCreate>): Promise<APIKey> => {
    return request<APIKey>(`/settings/api-keys/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  deleteAPIKey: async (id: string): Promise<void> => {
    return request<void>(`/settings/api-keys/${id}`, { method: 'DELETE' })
  },

  testAPIKey: async (id: string): Promise<{ valid: boolean; message: string }> => {
    return request<{ valid: boolean; message: string }>(`/settings/api-keys/${id}/test`, {
      method: 'POST',
    })
  },

  // AI Models
  listAIModels: async (provider?: string): Promise<AIModel[]> => {
    const query = provider ? `?provider=${provider}` : ''
    return request<AIModel[]>(`/settings/models${query}`)
  },

  listAIProviders: async (): Promise<AIProvider[]> => {
    return request<AIProvider[]>('/settings/models/providers')
  },

  // Agent Topics (Conversation Flows)
  listAgentTopics: async (agentId: string): Promise<AgentTopic[]> => {
    return request<AgentTopic[]>(`/settings/agents/${agentId}/topics`)
  },

  createAgentTopic: async (agentId: string, data: TopicCreate): Promise<AgentTopic> => {
    return request<AgentTopic>(`/settings/agents/${agentId}/topics`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteAgentTopic: async (agentId: string, topicId: string): Promise<void> => {
    return request<void>(`/settings/agents/${agentId}/topics/${topicId}`, { method: 'DELETE' })
  },

  // Agent Actions (Connectors)
  listAgentActions: async (agentId: string): Promise<AgentAction[]> => {
    return request<AgentAction[]>(`/settings/agents/${agentId}/actions`)
  },

  createAgentAction: async (agentId: string, data: ActionCreate): Promise<AgentAction> => {
    return request<AgentAction>(`/settings/agents/${agentId}/actions`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteAgentAction: async (agentId: string, actionId: string): Promise<void> => {
    return request<void>(`/settings/agents/${agentId}/actions/${actionId}`, { method: 'DELETE' })
  },

  // Agent Knowledge Base
  listAgentKnowledge: async (agentId: string): Promise<AgentKnowledge[]> => {
    return request<AgentKnowledge[]>(`/settings/agents/${agentId}/knowledge`)
  },

  createAgentKnowledge: async (agentId: string, data: KnowledgeCreate): Promise<AgentKnowledge> => {
    return request<AgentKnowledge>(`/settings/agents/${agentId}/knowledge`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  deleteAgentKnowledge: async (agentId: string, knowledgeId: string): Promise<void> => {
    return request<void>(`/settings/agents/${agentId}/knowledge/${knowledgeId}`, { method: 'DELETE' })
  },

  // ============================================
  // FILE UPLOADS - For chat file attachments
  // ============================================

  uploadFile: async (file: File): Promise<{
    id: string
    filename: string
    content_type: string
    size: number
    extracted_text: string | null
    data_uri: string | null
    metadata: Record<string, unknown>
  }> => {
    const form = new FormData()
    form.append('file', file)
    return request(`/files/upload`, {
      method: 'POST',
      body: form,
    })
  },

  uploadMultipleFiles: async (files: File[]): Promise<{
    files: Array<{
      id: string
      filename: string
      content_type?: string
      size?: number
      extracted_text?: string | null
      data_uri?: string | null
      metadata?: Record<string, unknown>
      error?: string
    }>
    count: number
  }> => {
    const form = new FormData()
    files.forEach(file => form.append('files', file))
    return request(`/files/upload-multiple`, {
      method: 'POST',
      body: form,
    })
  },

  getSupportedFileTypes: async (): Promise<{
    types: Record<string, string>
    max_size_mb: number
    categories: Record<string, string[]>
  }> => {
    return request(`/files/supported-types`)
  },
}
