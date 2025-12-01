import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowApi } from '../api/workflows';
import { ConfirmDialog } from '../components/ConfirmDialog';
import toast from 'react-hot-toast';

export const WorkflowList = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<string>('');
  const [deleteWorkflowId, setDeleteWorkflowId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const limit = 10;

  const { data, isLoading, error } = useQuery({
    queryKey: ['workflows', page, limit, search, sort],
    queryFn: () => workflowApi.getWorkflowsPaginated(page, limit, search || undefined, sort || undefined),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => workflowApi.deleteWorkflow(id),
    onSuccess: () => {
      toast.success('Workflow deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      setDeleteWorkflowId(null);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete workflow');
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  const workflows = data?.items || [];
  const totalPages = data?.pages || 0;

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Loading workflows...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Error loading workflows</p>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['workflows'] })}
          className="mt-2 text-blue-600 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Workflows</h2>
        <Link
          to="/create"
          className="bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Create New Workflow
        </Link>
      </div>

      {/* Search and Filter */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search workflows..."
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
            />
          </div>
          <div className="sm:w-48">
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
            >
              <option value="">Sort by...</option>
              <option value="name">Name (A-Z)</option>
              <option value="created_at">Created (Newest)</option>
              <option value="updated_at">Updated (Recent)</option>
            </select>
          </div>
          <button
            type="submit"
            className="bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            Search
          </button>
        </form>
      </div>

      {workflows.length === 0 ? (
        <div className="bg-white shadow rounded-lg p-12 text-center">
          <p className="text-gray-500 mb-4">
            {search ? 'No workflows found matching your search.' : 'No workflows yet. Create your first workflow to get started.'}
          </p>
          <Link
            to="/create"
            className="inline-block bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
          >
            Create Workflow
          </Link>
        </div>
      ) : (
        <>
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <ul className="divide-y divide-gray-200">
            {workflows.map((workflow) => (
              <li key={workflow.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex justify-between items-center">
                    <div className="flex-1">
                    <Link
                        to={`/workflow/${workflow.id}`}
                      className="text-lg font-medium text-blue-600 hover:text-blue-800"
                    >
                      {workflow.name}
                    </Link>
                    <p className="text-sm text-gray-500 mt-1">{workflow.description}</p>
                      <div className="text-xs text-gray-400 mt-1 space-x-4">
                        <span>Created: {new Date(workflow.created_at).toLocaleString()}</span>
                        <span>Updated: {new Date(workflow.updated_at).toLocaleString()}</span>
                      </div>
                  </div>
                    <div className="flex items-center space-x-3 ml-4">
                    <Link
                        to={`/workflow/${workflow.id}/edit`}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                        Edit
                    </Link>
                      <button
                        onClick={() => setDeleteWorkflowId(workflow.id)}
                        className="text-sm text-red-600 hover:text-red-800 font-medium"
                      >
                        Delete
                      </button>
                    <Link
                        to={`/workflow/${workflow.id}`}
                        className="text-sm text-gray-600 hover:text-gray-800 font-medium"
                    >
                        View
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between bg-white px-4 py-3 rounded-lg shadow sm:px-6">
              <div className="flex flex-1 justify-between sm:hidden">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing <span className="font-medium">{(page - 1) * limit + 1}</span> to{' '}
                    <span className="font-medium">{Math.min(page * limit, data?.total || 0)}</span> of{' '}
                    <span className="font-medium">{data?.total || 0}</span> results
                  </p>
                </div>
                <div>
                  <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (page <= 3) {
                        pageNum = i + 1;
                      } else if (page >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = page - 2 + i;
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setPage(pageNum)}
                          className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${
                            page === pageNum
                              ? 'z-10 bg-blue-600 text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                              : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {deleteWorkflowId && (
        <ConfirmDialog
          isOpen={!!deleteWorkflowId}
          title="Delete Workflow"
          message="Are you sure you want to delete this workflow? This action cannot be undone."
          confirmText="Delete"
          cancelText="Cancel"
          variant="danger"
          onConfirm={() => {
            if (deleteWorkflowId) {
              deleteMutation.mutate(deleteWorkflowId);
            }
          }}
          onCancel={() => setDeleteWorkflowId(null)}
        />
      )}
    </div>
  );
};

