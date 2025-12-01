import { useState, useEffect } from 'react';
import type { AgentCreate, AgentUpdate, Agent } from '../types';

interface AgentFormProps {
  onSubmit: (agent: AgentCreate | AgentUpdate) => void;
  onCancel: () => void;
  agent?: Agent;
}

export const AgentForm = ({ onSubmit, onCancel, agent }: AgentFormProps) => {
  const [name, setName] = useState('');
  const [role, setRole] = useState<AgentCreate['role']>('planner');
  const [status, setStatus] = useState<AgentCreate['agent_status']>('active');
  const [capabilities, setCapabilities] = useState<string>('');
  const [properties, setProperties] = useState<string>('');

  useEffect(() => {
    if (agent) {
      setName(agent.name);
      setRole(agent.role);
      setStatus(agent.agent_status);
      setCapabilities(agent.agent_capabilities?.join(', ') || '');
      setProperties(JSON.stringify(agent.agent_properties || {}, null, 2));
    }
  }, [agent]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      const agentData: AgentCreate | AgentUpdate = {
        name: name.trim(),
        role,
        agent_status: status,
        agent_capabilities: capabilities
          ? capabilities.split(',').map((c) => c.trim()).filter(Boolean)
          : undefined,
        agent_properties: properties
          ? (() => {
              try {
                return JSON.parse(properties);
              } catch {
                return {};
              }
            })()
          : undefined,
      };
      onSubmit(agentData);
      if (!agent) {
        setName('');
        setRole('planner');
        setStatus('active');
        setCapabilities('');
        setProperties('');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        {agent ? 'Edit Agent' : 'Add New Agent'}
      </h3>
      <div className="space-y-4">
        <div>
          <label htmlFor="agent-name" className="block text-sm font-medium text-gray-700">
            Agent Name
          </label>
          <input
            type="text"
            id="agent-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
            placeholder="Enter agent name"
            required
          />
        </div>
        <div>
          <label htmlFor="agent-role" className="block text-sm font-medium text-gray-700">
            Role
          </label>
          <select
            id="agent-role"
            value={role}
            onChange={(e) => setRole(e.target.value as AgentCreate['role'])}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
          >
            <option value="planner">Planner</option>
            <option value="retriever">Retriever</option>
            <option value="evaluator">Evaluator</option>
            <option value="executor">Executor</option>
          </select>
        </div>
        <div>
          <label htmlFor="agent-status" className="block text-sm font-medium text-gray-700">
            Status
          </label>
          <select
            id="agent-status"
            value={status}
            onChange={(e) => setStatus(e.target.value as AgentCreate['agent_status'])}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="maintenance">Maintenance</option>
          </select>
        </div>
        <div>
          <label htmlFor="agent-capabilities" className="block text-sm font-medium text-gray-700">
            Capabilities (comma-separated)
          </label>
          <input
            type="text"
            id="agent-capabilities"
            value={capabilities}
            onChange={(e) => setCapabilities(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
            placeholder="e.g., search, analyze, execute"
          />
        </div>
        <div>
          <label htmlFor="agent-properties" className="block text-sm font-medium text-gray-700">
            Properties (JSON)
          </label>
          <textarea
            id="agent-properties"
            value={properties}
            onChange={(e) => setProperties(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border font-mono text-xs"
            placeholder='{"key": "value"}'
            rows={4}
          />
        </div>
        <div className="flex space-x-2">
          <button
            type="submit"
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            {agent ? 'Update Agent' : 'Add Agent'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            Cancel
          </button>
        </div>
      </div>
    </form>
  );
};

