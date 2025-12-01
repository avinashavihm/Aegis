import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { templateApi } from '../api/templates';
import type { WorkflowTemplate } from '../types';
import toast from 'react-hot-toast';
import { ConfirmDialog } from '../components/ConfirmDialog';

export const Templates = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showApplyDialog, setShowApplyDialog] = useState<WorkflowTemplate | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [showDeleteDialog, setShowDeleteDialog] = useState<WorkflowTemplate | null>(null);

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: () => templateApi.getTemplates(),
  });

  const applyMutation = useMutation({
    mutationFn: ({ template, name, description }: { template: WorkflowTemplate; name: string; description?: string }) =>
      templateApi.applyTemplate(template.id, name, description),
    onSuccess: (workflow) => {
      toast.success('Workflow created from template');
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      navigate(`/workflow/${workflow.id}`);
      setShowApplyDialog(null);
      setWorkflowName('');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to apply template');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (templateId: string) => templateApi.deleteTemplate(templateId),
    onSuccess: () => {
      toast.success('Template deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      setShowDeleteDialog(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete template');
    },
  });

  const handleApply = () => {
    if (showApplyDialog && workflowName.trim()) {
      applyMutation.mutate({
        template: showApplyDialog,
        name: workflowName.trim(),
      });
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading templates...</p>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="mb-6">
        <Link to="/" className="text-blue-600 hover:text-blue-800 text-sm mb-2 inline-block">
          ← Back to Workflows
        </Link>
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Workflow Templates</h2>
            <p className="text-gray-600 mt-1">Browse and apply workflow templates</p>
          </div>
        </div>
      </div>

      {templates.length === 0 ? (
        <div className="text-center py-12 bg-white shadow rounded-lg">
          <p className="text-gray-500">No templates available</p>
          <p className="text-sm text-gray-400 mt-2">
            Templates allow you to quickly create workflows from pre-configured setups
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
            <div key={template.id} className="bg-white shadow rounded-lg overflow-hidden">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{template.name}</h3>
                {template.description && (
                  <p className="text-sm text-gray-600 mb-4">{template.description}</p>
                )}
                <div className="text-xs text-gray-500 mb-4">
                  Created: {new Date(template.created_at).toLocaleDateString()}
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => {
                      setShowApplyDialog(template);
                      setWorkflowName('');
                    }}
                    className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 text-sm"
                  >
                    Apply
                  </button>
                  <button
                    onClick={() => setShowDeleteDialog(template)}
                    className="bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={!!showApplyDialog}
        title="Apply Template"
        message={
          <div className="space-y-4">
            <p>Enter a name for the new workflow:</p>
            <input
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              placeholder="Workflow name"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              autoFocus
            />
          </div>
        }
        confirmText="Create Workflow"
        cancelText="Cancel"
        variant="primary"
        onConfirm={handleApply}
        onCancel={() => {
          setShowApplyDialog(null);
          setWorkflowName('');
        }}
      />

      <ConfirmDialog
        isOpen={!!showDeleteDialog}
        title="Delete Template"
        message={`Are you sure you want to delete "${showDeleteDialog?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        onConfirm={() => {
          if (showDeleteDialog) {
            deleteMutation.mutate(showDeleteDialog.id);
          }
        }}
        onCancel={() => setShowDeleteDialog(null)}
      />
    </div>
  );
};

