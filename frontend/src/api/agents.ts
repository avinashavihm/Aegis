import { apiClient } from './client';
import type { Agent, AgentUpdate } from '../types';

export const agentApi = {
  // Update an agent
  updateAgent: async (
    workflowId: string,
    agentId: string,
    data: AgentUpdate
  ): Promise<Agent> => {
    const response = await apiClient.put<Agent>(
      `/api/v1/workflow/${workflowId}/agents/${agentId}`,
      data
    );
    return response.data;
  },

  // Delete an agent
  deleteAgent: async (workflowId: string, agentId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/workflow/${workflowId}/agents/${agentId}`);
  },
};

