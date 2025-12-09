import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Run } from '../api/types'

export default function Runs() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // View detail
  const [selectedRun, setSelectedRun] = useState<Run | null>(null)

  const loadData = async () => {
    try {
      const data = await api.listRuns(50)
      setRuns(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const refreshRun = async (id: string) => {
    try {
      const run = await api.getRun(id)
      setSelectedRun(run)
      // Also update in list
      setRuns(runs.map(r => r.id === id ? run : r))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh run')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Runs</h1>
      {error && <div className="error">{error}</div>}

      <button className="btn btn-secondary" onClick={loadData} style={{ marginBottom: 16 }}>
        Refresh
      </button>

      {selectedRun && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Run Details</h3>
            <div>
              <button className="btn btn-secondary" onClick={() => refreshRun(selectedRun.id)} style={{ marginRight: 8 }}>
                Refresh
              </button>
              <button className="btn btn-secondary" onClick={() => setSelectedRun(null)}>
                Close
              </button>
            </div>
          </div>

          <p><strong>ID:</strong> {selectedRun.id}</p>
          <p><strong>Type:</strong> {selectedRun.run_type}</p>
          <p>
            <strong>Status:</strong>{' '}
            <span className={`status-badge status-${selectedRun.status}`}>{selectedRun.status}</span>
          </p>
          <p><strong>Agent ID:</strong> {selectedRun.agent_id || '-'}</p>
          <p><strong>Workflow ID:</strong> {selectedRun.workflow_id || '-'}</p>
          <p><strong>Tokens Used:</strong> {selectedRun.tokens_used}</p>
          <p><strong>Started:</strong> {selectedRun.started_at ? new Date(selectedRun.started_at).toLocaleString() : '-'}</p>
          <p><strong>Completed:</strong> {selectedRun.completed_at ? new Date(selectedRun.completed_at).toLocaleString() : '-'}</p>

          <h4>Input Message</h4>
          <pre>{selectedRun.input_message}</pre>

          {selectedRun.output && (
            <>
              <h4>Output</h4>
              <pre>{selectedRun.output}</pre>
            </>
          )}

          {selectedRun.error && (
            <>
              <h4>Error</h4>
              <div className="error">{selectedRun.error}</div>
            </>
          )}

          {selectedRun.context_variables && Object.keys(selectedRun.context_variables).length > 0 && (
            <>
              <h4>Context Variables</h4>
              <pre>{JSON.stringify(selectedRun.context_variables, null, 2)}</pre>
            </>
          )}

          {selectedRun.messages && selectedRun.messages.length > 0 && (
            <>
              <h4>Messages ({selectedRun.messages.length})</h4>
              <pre style={{ maxHeight: 300, overflow: 'auto' }}>{JSON.stringify(selectedRun.messages, null, 2)}</pre>
            </>
          )}

          {selectedRun.tool_calls && selectedRun.tool_calls.length > 0 && (
            <>
              <h4>Tool Calls ({selectedRun.tool_calls.length})</h4>
              <pre>{JSON.stringify(selectedRun.tool_calls, null, 2)}</pre>
            </>
          )}

          {selectedRun.step_results && selectedRun.step_results.length > 0 && (
            <>
              <h4>Step Results ({selectedRun.step_results.length})</h4>
              <pre>{JSON.stringify(selectedRun.step_results, null, 2)}</pre>
            </>
          )}
        </div>
      )}

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Input</th>
            <th>Tokens</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map(run => (
            <tr key={run.id}>
              <td style={{ fontSize: 12, fontFamily: 'monospace' }}>{run.id.substring(0, 8)}...</td>
              <td>{run.run_type}</td>
              <td><span className={`status-badge status-${run.status}`}>{run.status}</span></td>
              <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {run.input_message}
              </td>
              <td>{run.tokens_used}</td>
              <td>{new Date(run.created_at).toLocaleString()}</td>
              <td>
                <button className="btn btn-secondary" onClick={() => setSelectedRun(run)}>View</button>
              </td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td colSpan={7} style={{ textAlign: 'center', padding: 40 }}>No runs yet</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
