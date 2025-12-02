import { useParams, Link } from 'react-router-dom';
import { useWorkflow } from '../hooks/useWorkflows';
import { DependencyManager } from '../components/DependencyManager';

export const DefineDependencies = () => {
  const { id } = useParams<{ id: string }>();
  const { data: workflow, isLoading, error } = useWorkflow(id || '');

  if (isLoading) {
    return <div className="text-center py-8">Loading workflow...</div>;
  }

  if (error || !workflow) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">Workflow not found</p>
        <Link to="/" className="text-blue-600 hover:text-blue-800">
          Back to Workflows
        </Link>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="mb-6">
        <Link to="/" className="text-blue-600 hover:text-blue-800 text-sm mb-2 inline-block">
          ← Back to Workflows
        </Link>
        <h2 className="text-2xl font-bold text-gray-900">{workflow.name}</h2>
        <p className="text-gray-600 mt-1">{workflow.description}</p>
      </div>

      <div className="mb-6">
        <Link
          to={`/workflow/${id}/agents`}
          className="text-blue-600 hover:text-blue-800 text-sm"
        >
          ← Manage Agents
        </Link>
      </div>

      <DependencyManager workflowId={id!} />
    </div>
  );
};

