import { useState, useEffect, useRef } from 'react';
import { useAgents, useDependencies, useUpdateDependencies } from '../hooks/useWorkflows';
import type { DependencyCreate, Agent } from '../types';

interface DependencyManagerProps {
  workflowId: string;
}

export const DependencyManager = ({ workflowId }: DependencyManagerProps) => {
  const { data: agents = [], isLoading: agentsLoading } = useAgents(workflowId);
  const { data: dependencies = [], isLoading: depsLoading } = useDependencies(workflowId);
  const updateDependencies = useUpdateDependencies(workflowId);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // State for managing dependencies
  const [agentDependencies, setAgentDependencies] = useState<Record<string, string[]>>({});
  const prevDepsRef = useRef<string>('');
  const prevAgentsRef = useRef<string>('');

  useEffect(() => {
    // Initialize agentDependencies from existing dependencies
    // Only update if agents or dependencies actually change
    if (agentsLoading || depsLoading) {
      return;
    }
    
    if (agents.length === 0) {
      setAgentDependencies({});
      prevAgentsRef.current = '';
      prevDepsRef.current = '';
      return;
    }
    
    // Create stable string representations for comparison
    const agentsStr = JSON.stringify(agents.map(a => a.id).sort());
    const depsStr = JSON.stringify(dependencies.map(d => `${d.agent_id}-${d.depends_on_agent_id}`).sort());
    
    // Only update if agents or dependencies actually changed
    if (agentsStr === prevAgentsRef.current && depsStr === prevDepsRef.current) {
      return;
    }
    
    prevAgentsRef.current = agentsStr;
    prevDepsRef.current = depsStr;
    
    const depsMap: Record<string, string[]> = {};
    agents.forEach((agent) => {
      depsMap[agent.id] = [];
    });
    dependencies.forEach((dep) => {
      if (!depsMap[dep.agent_id]) {
        depsMap[dep.agent_id] = [];
      }
      depsMap[dep.agent_id].push(dep.depends_on_agent_id);
    });
    
    setAgentDependencies(depsMap);
  }, [dependencies, agents, agentsLoading, depsLoading]);

  const handleDependencyChange = (agentId: string, dependsOnAgentId: string, checked: boolean) => {
    setAgentDependencies((prev) => {
      const current = prev[agentId] || [];
      if (checked) {
        return { ...prev, [agentId]: [...current, dependsOnAgentId] };
      } else {
        return { ...prev, [agentId]: current.filter((id) => id !== dependsOnAgentId) };
      }
    });
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);

    // Build dependency list
    const deps: DependencyCreate[] = [];
    Object.entries(agentDependencies).forEach(([agentId, dependsOnIds]) => {
      dependsOnIds.forEach((dependsOnId) => {
        deps.push({ agent_id: agentId, depends_on_agent_id: dependsOnId });
      });
    });

    try {
      await updateDependencies.mutateAsync(deps);
      setSuccess('Dependencies saved successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save dependencies. Check for cycles.');
    }
  };

  if (agentsLoading || depsLoading) {
    return <div className="text-center py-4">Loading...</div>;
  }

  if (agents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No agents found. Please add agents first before defining dependencies.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Agent Dependencies</h3>
        <button
          onClick={handleSave}
          disabled={updateDependencies.isPending}
          className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {updateDependencies.isPending ? 'Saving...' : 'Save Dependencies'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {success}
        </div>
      )}

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <p className="text-sm text-gray-600">
            Select which agents each agent depends on. The system will validate that there are no cycles.
          </p>
        </div>
        <div className="divide-y divide-gray-200">
          {agents.map((agent) => (
            <div key={agent.id} className="px-6 py-4">
              <div className="mb-3">
                <span className="text-sm font-medium text-gray-900">{agent.name}</span>
                <span className="ml-2 text-xs text-gray-500 capitalize">({agent.role})</span>
                <span className="ml-2 text-sm text-gray-600">depends on:</span>
              </div>
              <div className="space-y-2">
                {agents
                  .filter((a) => a.id !== agent.id)
                  .map((dependsOnAgent) => (
                    <label
                      key={dependsOnAgent.id}
                      className="flex items-center space-x-2 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={agentDependencies[agent.id]?.includes(dependsOnAgent.id) || false}
                        onChange={(e) =>
                          handleDependencyChange(agent.id, dependsOnAgent.id, e.target.checked)
                        }
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">
                        {dependsOnAgent.name} <span className="text-gray-500">({dependsOnAgent.role})</span>
                      </span>
                    </label>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Visual confirmation */}
      {Object.keys(agentDependencies).some((key) => agentDependencies[key].length > 0) && (
        <div className="bg-white shadow rounded-lg p-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">Dependency Summary</h4>
          <div className="space-y-2">
            {agents.map((agent) => {
              const deps = agentDependencies[agent.id] || [];
              if (deps.length === 0) return null;
              const depAgents = agents.filter((a) => deps.includes(a.id));
              return (
                <div key={agent.id} className="text-sm">
                  <span className="font-medium text-gray-900">{agent.name}</span>
                  <span className="text-gray-600"> → </span>
                  <span className="text-gray-700">
                    {depAgents.map((a) => a.name).join(', ')}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

