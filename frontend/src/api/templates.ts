import { apiClient } from './client';
import type {
  WorkflowTemplate,
  WorkflowTemplateCreate,
  WorkflowTemplateUpdate,
  Workflow,
} from '../types';

export const templateApi = {
  // Create a template
  createTemplate: async (data: WorkflowTemplateCreate): Promise<WorkflowTemplate> => {
    const response = await apiClient.post<WorkflowTemplate>(
      '/api/v1/templates',
      data
    );
    return response.data;
  },

  // Get all templates
  getTemplates: async (): Promise<WorkflowTemplate[]> => {
    const response = await apiClient.get<WorkflowTemplate[]>('/api/v1/templates');
    return response.data;
  },

  // Get template by ID
  getTemplate: async (templateId: string): Promise<WorkflowTemplate> => {
    const response = await apiClient.get<WorkflowTemplate>(
      `/api/v1/templates/${templateId}`
    );
    return response.data;
  },

  // Update a template
  updateTemplate: async (
    templateId: string,
    data: WorkflowTemplateUpdate
  ): Promise<WorkflowTemplate> => {
    const response = await apiClient.put<WorkflowTemplate>(
      `/api/v1/templates/${templateId}`,
      data
    );
    return response.data;
  },

  // Delete a template
  deleteTemplate: async (templateId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/templates/${templateId}`);
  },

  // Apply a template to create a workflow
  applyTemplate: async (
    templateId: string,
    workflowName: string,
    workflowDescription?: string,
    overrides?: Record<string, any>
  ): Promise<Workflow> => {
    const response = await apiClient.post<Workflow>(
      `/api/v1/templates/${templateId}/apply`,
      {
        template_id: templateId,
        workflow_name: workflowName,
        workflow_description: workflowDescription,
        overrides,
      }
    );
    return response.data;
  },
};

