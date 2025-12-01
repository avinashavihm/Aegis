import { apiClient } from './client';
import type {
  Workflow,
  WorkflowCreate,
  WorkflowUpdate,
  Agent,
  AgentCreate,
  Dependency,
  DependencyCreate,
  PaginatedResponse,
} from '../types';

export const workflowApi = {
  // Workflow operations
  createWorkflow: async (data: WorkflowCreate): Promise<Workflow> => {
    const response = await apiClient.post<Workflow>('/api/v1/workflow', data);
    return response.data;
  },

  getWorkflow: async (id: string): Promise<Workflow> => {
    const response = await apiClient.get<Workflow>(`/api/v1/workflow/${id}`);
    return response.data;
  },

  updateWorkflow: async (id: string, data: WorkflowUpdate): Promise<Workflow> => {
    const response = await apiClient.put<Workflow>(`/api/v1/workflow/${id}`, data);
    return response.data;
  },

  deleteWorkflow: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/workflow/${id}`);
  },

  getWorkflows: async (): Promise<Workflow[]> => {
    const response = await apiClient.get<Workflow[]>('/api/v1/workflow');
    return response.data;
  },

  getWorkflowsPaginated: async (
    page: number = 1,
    limit: number = 10,
    search?: string,
    sort?: string
  ): Promise<PaginatedResponse<Workflow>> => {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });
    if (search) params.append('search', search);
    if (sort) params.append('sort', sort);
    const response = await apiClient.get<PaginatedResponse<Workflow>>(
      `/api/v1/workflow?${params.toString()}`
    );
    return response.data;
  },

  // Agent operations
  getAgents: async (workflowId: string): Promise<Agent[]> => {
    const response = await apiClient.get<Agent[]>(`/api/v1/workflow/${workflowId}/agents`);
    return response.data;
  },

  updateAgents: async (workflowId: string, agents: AgentCreate[]): Promise<Agent[]> => {
    const response = await apiClient.put<Agent[]>(`/api/v1/workflow/${workflowId}/agents`, { agents });
    return response.data;
  },

  // Dependency operations
  getDependencies: async (workflowId: string): Promise<Dependency[]> => {
    const response = await apiClient.get<Dependency[]>(`/api/v1/workflow/${workflowId}/dependencies`);
    return response.data;
  },

  updateDependencies: async (workflowId: string, dependencies: DependencyCreate[]): Promise<Dependency[]> => {
    const response = await apiClient.put<Dependency[]>(`/api/v1/workflow/${workflowId}/dependencies`, { dependencies });
    return response.data;
  },

  // Export workflow
  exportWorkflow: async (workflowId: string, format: 'json' | 'yaml' = 'json'): Promise<Blob> => {
    const response = await apiClient.get(
      `/api/v1/workflow/${workflowId}/export?format=${format}`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  // Import workflow
  importWorkflow: async (
    file: File,
    workflowName?: string,
    workflowDescription?: string
  ): Promise<Workflow> => {
    const format = file.name.endsWith('.yaml') || file.name.endsWith('.yml') ? 'yaml' : 'json';
    const content = await file.text();
    
    const params = new URLSearchParams({ format });
    if (workflowName) params.append('workflow_name', workflowName);
    if (workflowDescription) params.append('workflow_description', workflowDescription);
    
    const response = await apiClient.post<Workflow>(
      `/api/v1/workflow/import?${params.toString()}`,
      content,
      {
        headers: {
          'Content-Type': format === 'yaml' ? 'application/x-yaml' : 'application/json',
        },
      }
    );
    return response.data;
  },
};

