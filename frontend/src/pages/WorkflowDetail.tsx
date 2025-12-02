import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowApi } from '../api/workflows';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { DependencyGraph } from '../components/DependencyGraph';
import { useState, useRef } from 'react';
import toast from 'react-hot-toast';

export const WorkflowDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const { data: workflow, isLoading, error } = useQuery({
    queryKey: ['workflow', id],
    queryFn: () => workflowApi.getWorkflow(id!),
    enabled: !!id,
  });

  const { data: agents = [] } = useQuery({
    queryKey: ['agents', id],
    queryFn: () => workflowApi.getAgents(id!),
    enabled: !!id,
  });

  const { data: dependencies = [] } = useQuery({
    queryKey: ['dependencies', id],
    queryFn: () => workflowApi.getDependencies(id!),
    enabled: !!id,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => workflowApi.deleteWorkflow(id!),
    onSuccess: () => {
      toast.success('Workflow deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      navigate('/');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete workflow');
    },
  });

  const exportMutation = useMutation({
    mutationFn: (format: 'json' | 'yaml') => workflowApi.exportWorkflow(id!, format),
    onSuccess: async (blob, format) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workflow_${id}_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Workflow exported as ${format.toUpperCase()}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to export workflow');
    },
  });

  const importMutation = useMutation({
    mutationFn: (file: File) => workflowApi.importWorkflow(file),
    onSuccess: (workflow) => {
      toast.success('Workflow imported successfully');
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      navigate(`/workflow/${workflow.id}`);
      setShowImportDialog(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to import workflow');
    },
  });

  const handleExport = (format: 'json' | 'yaml') => {
    exportMutation.mutate(format);
  };

  const handleImport = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      importMutation.mutate(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading workflow...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Error loading workflow</p>
        <Link to="/" className="text-blue-600 hover:underline mt-2 inline-block">
          Back to workflows
        </Link>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-600">Workflow not found</p>
        <Link to="/" className="text-blue-600 hover:underline mt-2 inline-block">
          Back to workflows
        </Link>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="mb-6">
        <Link
          to="/"
          className="text-blue-600 hover:text-blue-800 text-sm font-medium mb-4 inline-block"
        >
          ← Back to workflows
        </Link>
        <div className="flex justify-between items-start mt-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{workflow.name}</h2>
            <p className="text-gray-600 mt-2">{workflow.description}</p>
            <div className="mt-4 text-sm text-gray-500">
              <p>Created: {new Date(workflow.created_at).toLocaleString()}</p>
              <p>Updated: {new Date(workflow.updated_at).toLocaleString()}</p>
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => handleExport('json')}
              className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            >
              Export JSON
            </button>
            <button
              onClick={() => handleExport('yaml')}
              className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
            >
              Export YAML
            </button>
            <button
              onClick={handleImport}
              className="bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2"
            >
              Import
            </button>
            <Link
              to={`/workflow/${id}/edit`}
              className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Edit
            </Link>
            <button
              onClick={() => setShowDeleteDialog(true)}
              className="bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            >
              Delete
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.yaml,.yml"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>
      </div>

      {/* Dependency Graph Visualization */}
      {agents.length > 0 && (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Dependency Graph</h3>
          <DependencyGraph agents={agents} dependencies={dependencies} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Agents</h3>
          {agents.length === 0 ? (
            <p className="text-gray-500 text-sm">No agents defined</p>
          ) : (
            <ul className="space-y-2">
              {agents.map((agent) => (
                <li key={agent.id} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <div>
                    <p className="font-medium text-gray-900">{agent.name}</p>
                    <p className="text-sm text-gray-500 capitalize">{agent.role}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <Link
            to={`/workflow/${id}/agents`}
            className="mt-4 inline-block text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Manage Agents →
          </Link>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Dependencies</h3>
          {dependencies.length === 0 ? (
            <p className="text-gray-500 text-sm">No dependencies defined</p>
          ) : (
            <ul className="space-y-2">
              {dependencies.map((dep) => {
                const agent = agents.find((a) => a.id === dep.agent_id);
                const dependsOn = agents.find((a) => a.id === dep.depends_on_agent_id);
                return (
                  <li key={dep.id} className="p-3 bg-gray-50 rounded text-sm">
                    <span className="font-medium">{agent?.name || dep.agent_id}</span>
                    <span className="text-gray-500 mx-2">depends on</span>
                    <span className="font-medium">{dependsOn?.name || dep.depends_on_agent_id}</span>
                  </li>
                );
              })}
            </ul>
          )}
          <Link
            to={`/workflow/${id}/dependencies`}
            className="mt-4 inline-block text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Manage Dependencies →
          </Link>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showDeleteDialog}
        title="Delete Workflow"
        message={`Are you sure you want to delete "${workflow.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={() => {
          deleteMutation.mutate();
          setShowDeleteDialog(false);
        }}
        onCancel={() => setShowDeleteDialog(false)}
      />
    </div>
  );
};

