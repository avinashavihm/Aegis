import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { executionApi } from '../api/executions';
import type { WorkflowExecution, ExecutionDetail } from '../types';

export const Executions = () => {
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);
  const [workflowFilter, setWorkflowFilter] = useState<string>('');

  const { data: executions = [], isLoading } = useQuery({
    queryKey: ['executions', workflowFilter || undefined],
    queryFn: () => executionApi.getExecutions(workflowFilter || undefined),
  });

  const { data: executionDetail } = useQuery({
    queryKey: ['execution', selectedExecution],
    queryFn: () => executionApi.getExecution(selectedExecution!),
    enabled: !!selectedExecution,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading executions...</p>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="mb-6">
        <Link to="/" className="text-blue-600 hover:text-blue-800 text-sm mb-2 inline-block">
          ← Back to Workflows
        </Link>
        <h2 className="text-2xl font-bold text-gray-900">Execution Dashboard</h2>
        <p className="text-gray-600 mt-1">View and monitor workflow executions</p>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Filter by workflow ID (optional)"
          value={workflowFilter}
          onChange={(e) => setWorkflowFilter(e.target.value)}
          className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Execution History</h3>
          </div>
          {executions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No executions found
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {executions.map((execution) => (
                <li
                  key={execution.id}
                  className={`px-6 py-4 cursor-pointer hover:bg-gray-50 ${
                    selectedExecution === execution.id ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => setSelectedExecution(execution.id)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">
                          {execution.workflow_id}
                        </span>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                            execution.status
                          )}`}
                        >
                          {execution.status}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {execution.started_at
                          ? `Started: ${new Date(execution.started_at).toLocaleString()}`
                          : 'Not started'}
                      </div>
                      {execution.completed_at && (
                        <div className="text-xs text-gray-500">
                          Completed: {new Date(execution.completed_at).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Execution Details</h3>
          </div>
          {selectedExecution && executionDetail ? (
            <div className="p-6 space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-700">Status</h4>
                <span
                  className={`inline-block mt-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                    executionDetail.execution.status
                  )}`}
                >
                  {executionDetail.execution.status}
                </span>
              </div>
              {executionDetail.execution.started_at && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Started At</h4>
                  <p className="text-sm text-gray-900 mt-1">
                    {new Date(executionDetail.execution.started_at).toLocaleString()}
                  </p>
                </div>
              )}
              {executionDetail.execution.completed_at && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Completed At</h4>
                  <p className="text-sm text-gray-900 mt-1">
                    {new Date(executionDetail.execution.completed_at).toLocaleString()}
                  </p>
                </div>
              )}
              {executionDetail.execution.logs && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700">Logs</h4>
                  <pre className="mt-1 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-40">
                    {executionDetail.execution.logs}
                  </pre>
                </div>
              )}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Agent Executions</h4>
                <div className="space-y-2">
                  {executionDetail.agent_executions.map((ae) => (
                    <div key={ae.id} className="p-3 bg-gray-50 rounded">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900">
                          Agent: {ae.agent_id}
                        </span>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                            ae.status
                          )}`}
                        >
                          {ae.status}
                        </span>
                      </div>
                      {ae.output && (
                        <pre className="mt-2 text-xs text-gray-600 overflow-auto max-h-20">
                          {ae.output}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Select an execution to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

