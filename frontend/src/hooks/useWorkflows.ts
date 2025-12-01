import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowApi } from '../api/workflows';
import type { WorkflowCreate, AgentCreate, DependencyCreate } from '../types';

// Query keys
export const queryKeys = {
  workflows: ['workflows'] as const,
  workflow: (id: string) => ['workflow', id] as const,
  agents: (workflowId: string) => ['agents', workflowId] as const,
  dependencies: (workflowId: string) => ['dependencies', workflowId] as const,
};

// Workflow hooks
export const useWorkflows = () => {
  return useQuery({
    queryKey: queryKeys.workflows,
    queryFn: workflowApi.getWorkflows,
  });
};

export const useWorkflow = (id: string, options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: queryKeys.workflow(id),
    queryFn: () => workflowApi.getWorkflow(id),
    enabled: options?.enabled !== false && !!id,
  });
};

export const useCreateWorkflow = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: workflowApi.createWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.workflows });
    },
  });
};

// Agent hooks
export const useAgents = (workflowId: string) => {
  return useQuery({
    queryKey: queryKeys.agents(workflowId),
    queryFn: () => workflowApi.getAgents(workflowId),
    enabled: !!workflowId,
  });
};

export const useUpdateAgents = (workflowId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (agents: AgentCreate[]) => workflowApi.updateAgents(workflowId, agents),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents(workflowId) });
    },
  });
};

// Dependency hooks
export const useDependencies = (workflowId: string) => {
  return useQuery({
    queryKey: queryKeys.dependencies(workflowId),
    queryFn: () => workflowApi.getDependencies(workflowId),
    enabled: !!workflowId,
  });
};

export const useUpdateDependencies = (workflowId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dependencies: DependencyCreate[]) => workflowApi.updateDependencies(workflowId, dependencies),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.dependencies(workflowId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.agents(workflowId) });
    },
  });
};

