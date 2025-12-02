import { apiClient } from './client';
import type {
  WorkflowExecution,
  ExecutionDetail,
} from '../types';

export const executionApi = {
  // Execute a workflow
  executeWorkflow: async (workflowId: string): Promise<WorkflowExecution> => {
    const response = await apiClient.post<WorkflowExecution>(
      `/api/v1/executions/workflow/${workflowId}/execute`
    );
    return response.data;
  },

  // Get all executions
  getExecutions: async (workflowId?: string): Promise<WorkflowExecution[]> => {
    const params = workflowId ? `?workflow_id=${workflowId}` : '';
    const response = await apiClient.get<WorkflowExecution[]>(
      `/api/v1/executions${params}`
    );
    return response.data;
  },

  // Get execution details
  getExecution: async (executionId: string): Promise<ExecutionDetail> => {
    const response = await apiClient.get<ExecutionDetail>(
      `/api/v1/executions/${executionId}`
    );
    return response.data;
  },
};

