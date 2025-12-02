import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowApi } from '../api/workflows';
import { agentApi } from '../api/agents';
import { AgentForm } from './AgentForm';
import type { Agent, AgentCreate, AgentUpdate } from '../types';
import toast from 'react-hot-toast';

interface AgentListProps {
  workflowId: string;
}

export const AgentList = ({ workflowId }: AgentListProps) => {
  const [showForm, setShowForm] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const queryClient = useQueryClient();

  const { data: agents = [], isLoading, error } = useQuery({
    queryKey: ['agents', workflowId],
    queryFn: () => workflowApi.getAgents(workflowId),
  });

  const updateAgents = useMutation({
    mutationFn: (agents: AgentCreate[]) => workflowApi.updateAgents(workflowId, agents),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', workflowId] });
      toast.success('Agents updated successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update agents');
    },
  });

  const updateAgent = useMutation({
    mutationFn: ({ agentId, data }: { agentId: string; data: AgentUpdate }) =>
      agentApi.updateAgent(workflowId, agentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', workflowId] });
      toast.success('Agent updated successfully');
      setEditingAgent(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update agent');
    },
  });

  const deleteAgent = useMutation({
    mutationFn: (agentId: string) => agentApi.deleteAgent(workflowId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', workflowId] });
      toast.success('Agent deleted successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete agent');
    },
  });

  const handleAddAgent = async (agent: AgentCreate) => {
    const updatedAgents = [...agents.map(a => ({
      name: a.name,
      role: a.role,
      agent_properties: a.agent_properties,
      agent_capabilities: a.agent_capabilities,
      agent_status: a.agent_status,
    })), agent];
    await updateAgents.mutateAsync(updatedAgents);
    setShowForm(false);
  };

  const handleEditAgent = async (agent: AgentUpdate) => {
    if (editingAgent) {
      await updateAgent.mutateAsync({ agentId: editingAgent.id, data: agent });
    }
  };

  const handleRemoveAgent = async (agentId: string) => {
    if (confirm('Are you sure you want to delete this agent?')) {
      await deleteAgent.mutateAsync(agentId);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'maintenance':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return <div className="text-center py-4">Loading agents...</div>;
  }

  if (error) {
    return <div className="text-center py-4 text-red-600">Error loading agents</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Agents</h3>
        {!showForm && !editingAgent && (
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Add Agent
          </button>
        )}
      </div>

      {(showForm || editingAgent) && (
        <AgentForm
          agent={editingAgent || undefined}
          onSubmit={editingAgent ? handleEditAgent : handleAddAgent}
          onCancel={() => {
            setShowForm(false);
            setEditingAgent(null);
          }}
        />
      )}

      {agents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No agents yet. Add your first agent to get started.
        </div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <ul className="divide-y divide-gray-200">
            {agents.map((agent) => (
              <li key={agent.id} className="px-6 py-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="text-sm font-medium text-gray-900">{agent.name}</div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(agent.agent_status)}`}>
                        {agent.agent_status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500 capitalize mt-1">{agent.role}</div>
                    {agent.agent_capabilities && agent.agent_capabilities.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {agent.agent_capabilities.map((cap, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800"
                          >
                            {cap}
                          </span>
                        ))}
                      </div>
                    )}
                    {agent.agent_properties && Object.keys(agent.agent_properties).length > 0 && (
                      <div className="mt-2 text-xs text-gray-500">
                        <details>
                          <summary className="cursor-pointer text-blue-600 hover:text-blue-800">
                            View Properties
                          </summary>
                          <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-auto">
                            {JSON.stringify(agent.agent_properties, null, 2)}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => setEditingAgent(agent)}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleRemoveAgent(agent.id)}
                      className="text-red-600 hover:text-red-800 text-sm font-medium"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

