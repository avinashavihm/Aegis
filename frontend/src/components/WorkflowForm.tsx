import { useState, useEffect } from 'react';
import { useCreateWorkflow, useWorkflow } from '../hooks/useWorkflows';
import { useNavigate, useParams } from 'react-router-dom';
import { workflowApi } from '../api/workflows';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';

export const WorkflowForm = () => {
  const { id } = useParams<{ id: string }>();
  const isEditMode = !!id;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: existingWorkflow, isLoading: isLoadingWorkflow } = useWorkflow(id || '', {
    enabled: isEditMode,
  });

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{ name?: string; description?: string }>({});

  useEffect(() => {
    if (existingWorkflow) {
      setName(existingWorkflow.name);
      setDescription(existingWorkflow.description);
    }
  }, [existingWorkflow]);

  const createWorkflow = useCreateWorkflow();
  const updateWorkflow = useMutation({
    mutationFn: (data: { name: string; description: string }) =>
      workflowApi.updateWorkflow(id!, data),
    onSuccess: () => {
      toast.success('Workflow updated successfully');
      queryClient.invalidateQueries({ queryKey: ['workflow', id] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      navigate(`/workflow/${id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update workflow');
    },
  });

  const validate = () => {
    const newErrors: { name?: string; description?: string } = {};
    if (!name.trim()) {
      newErrors.name = 'Name is required';
    } else if (name.trim().length > 200) {
      newErrors.name = 'Name must be less than 200 characters';
    }
    if (!description.trim()) {
      newErrors.description = 'Description is required';
    } else if (description.trim().length > 1000) {
      newErrors.description = 'Description must be less than 1000 characters';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    if (!validate()) {
      return;
    }

    try {
      if (isEditMode) {
        await updateWorkflow.mutateAsync({ name: name.trim(), description: description.trim() });
      } else {
        const workflow = await createWorkflow.mutateAsync({
          name: name.trim(),
          description: description.trim(),
        });
        toast.success('Workflow created successfully');
      navigate(`/workflow/${workflow.id}/agents`);
      }
    } catch (err: any) {
      if (err.message) {
        toast.error(err.message);
      }
    }
  };

  if (isEditMode && isLoadingWorkflow) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading workflow...</p>
      </div>
    );
    }

  const isPending = createWorkflow.isPending || updateWorkflow.isPending;

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        {isEditMode ? 'Edit Workflow' : 'Create New Workflow'}
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700">
            Workflow Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (errors.name) setErrors({ ...errors, name: undefined });
            }}
            className={`mt-1 block w-full rounded-md shadow-sm focus:ring-blue-500 sm:text-sm px-3 py-2 border ${
              errors.name
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-blue-500'
            }`}
            placeholder="Enter workflow name"
            required
            aria-invalid={!!errors.name}
            aria-describedby={errors.name ? 'name-error' : undefined}
          />
          {errors.name && (
            <p id="name-error" className="mt-1 text-sm text-red-600" role="alert">
              {errors.name}
            </p>
          )}
        </div>
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700">
            Description <span className="text-red-500">*</span>
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => {
              setDescription(e.target.value);
              if (errors.description) setErrors({ ...errors, description: undefined });
            }}
            rows={4}
            className={`mt-1 block w-full rounded-md shadow-sm focus:ring-blue-500 sm:text-sm px-3 py-2 border ${
              errors.description
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-blue-500'
            }`}
            placeholder="Enter workflow description"
            required
            aria-invalid={!!errors.description}
            aria-describedby={errors.description ? 'description-error' : undefined}
          />
          {errors.description && (
            <p id="description-error" className="mt-1 text-sm text-red-600" role="alert">
              {errors.description}
            </p>
          )}
        </div>
        <div className="flex space-x-3">
        <button
          type="submit"
            disabled={isPending}
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
            {isPending
              ? isEditMode
                ? 'Updating...'
                : 'Creating...'
              : isEditMode
              ? 'Update Workflow'
              : 'Create Workflow'}
          </button>
          {isEditMode && (
            <button
              type="button"
              onClick={() => navigate(`/workflow/${id}`)}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Cancel
        </button>
          )}
        </div>
      </form>
    </div>
  );
};

