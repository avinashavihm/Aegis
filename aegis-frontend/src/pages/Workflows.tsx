import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Workflow, Run } from '../api/types'

export default function Workflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [executionMode, setExecutionMode] = useState('sequential')
  const [tags, setTags] = useState('')
  const [status, setStatus] = useState('active')
  const [stepsJson, setStepsJson] = useState('[]')

  // Run workflow
  const [runWorkflowId, setRunWorkflowId] = useState('')
  const [inputMessage, setInputMessage] = useState('')
  const [runResult, setRunResult] = useState<Run | null>(null)
  const [runLoading, setRunLoading] = useState(false)

  // View detail
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)

  const loadData = async () => {
    try {
      const data = await api.listWorkflows()
      setWorkflows(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workflows')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const tagsList = tags.split(',').map(t => t.trim()).filter(t => t)
      const steps = JSON.parse(stepsJson)
      await api.createWorkflow({
        name,
        description,
        execution_mode: executionMode,
        tags: tagsList,
        status,
        steps
      })
      setShowCreate(false)
      setName('')
      setDescription('')
      setExecutionMode('sequential')
      setTags('')
      setStatus('active')
      setStepsJson('[]')
      loadData()
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON in steps field')
      } else {
        setError(err instanceof Error ? err.message : 'Failed to create workflow')
      }
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this workflow?')) return
    try {
      await api.deleteWorkflow(id)
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete workflow')
    }
  }

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault()
    setRunLoading(true)
    setRunResult(null)
    try {
      const result = await api.runWorkflow(runWorkflowId, {
        input_message: inputMessage,
        max_turns: 10
      })
      setRunResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run workflow')
    } finally {
      setRunLoading(false)
    }
  }

  const pollRunStatus = async (runId: string) => {
    try {
      const result = await api.getRun(runId)
      setRunResult(result)
      if (result.status === 'pending' || result.status === 'running') {
        setTimeout(() => pollRunStatus(runId), 2000)
      }
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    if (runResult && (runResult.status === 'pending' || runResult.status === 'running')) {
      const timeout = setTimeout(() => pollRunStatus(runResult.id), 2000)
      return () => clearTimeout(timeout)
    }
  }, [runResult])

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Workflows</h1>
      {error && <div className="error">{error}</div>}

      <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
        {showCreate ? 'Cancel' : 'Create Workflow'}
      </button>

      {showCreate && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Create Workflow</h3>
          <form onSubmit={handleCreate}>
            <input placeholder="Workflow Name" value={name} onChange={(e) => setName(e.target.value)} required />
            <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            <select value={executionMode} onChange={(e) => setExecutionMode(e.target.value)}>
              <option value="sequential">Sequential</option>
              <option value="parallel">Parallel</option>
            </select>
            <input placeholder="Tags (comma-separated)" value={tags} onChange={(e) => setTags(e.target.value)} />
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <label>Steps (JSON array)</label>
            <textarea
              placeholder='[{"action": "run_agent", "agent_id": "..."}]'
              value={stepsJson}
              onChange={(e) => setStepsJson(e.target.value)}
              rows={5}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
            <button type="submit" className="btn btn-success">Create</button>
          </form>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Run Workflow</h3>
        <form onSubmit={handleRun}>
          <select value={runWorkflowId} onChange={(e) => setRunWorkflowId(e.target.value)} required>
            <option value="">Select Workflow</option>
            {workflows.filter(w => w.status === 'active').map(w => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
          <textarea
            placeholder="Input message for the workflow..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            rows={3}
            required
          />
          <button type="submit" className="btn btn-primary" disabled={runLoading}>
            {runLoading ? 'Running...' : 'Run Workflow'}
          </button>
        </form>

        {runResult && (
          <div style={{ marginTop: 16 }}>
            <h4>Run Result</h4>
            <p><strong>Status:</strong> <span className={`status-badge status-${runResult.status}`}>{runResult.status}</span></p>
            <p><strong>Run ID:</strong> {runResult.id}</p>
            {runResult.output && (
              <div>
                <strong>Output:</strong>
                <pre>{runResult.output}</pre>
              </div>
            )}
            {runResult.error && (
              <div className="error">
                <strong>Error:</strong> {runResult.error}
              </div>
            )}
            {runResult.step_results && runResult.step_results.length > 0 && (
              <div>
                <strong>Step Results:</strong>
                <pre>{JSON.stringify(runResult.step_results, null, 2)}</pre>
              </div>
            )}
          </div>
        )}
      </div>

      {selectedWorkflow && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>{selectedWorkflow.name}</h3>
          <p>{selectedWorkflow.description || 'No description'}</p>
          <p><strong>Execution Mode:</strong> {selectedWorkflow.execution_mode}</p>
          <p><strong>Status:</strong> <span className={`status-badge status-${selectedWorkflow.status}`}>{selectedWorkflow.status}</span></p>
          <p><strong>Tags:</strong> {selectedWorkflow.tags?.join(', ') || 'None'}</p>
          <p><strong>Steps:</strong></p>
          <pre>{JSON.stringify(selectedWorkflow.steps, null, 2)}</pre>
          <button className="btn btn-secondary" onClick={() => setSelectedWorkflow(null)}>Close</button>
        </div>
      )}

      <table style={{ marginTop: 16 }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Execution Mode</th>
            <th>Status</th>
            <th>Steps</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {workflows.map(wf => (
            <tr key={wf.id}>
              <td>
                <a href="#" onClick={(e) => { e.preventDefault(); setSelectedWorkflow(wf) }}>{wf.name}</a>
              </td>
              <td>{wf.execution_mode}</td>
              <td><span className={`status-badge status-${wf.status}`}>{wf.status}</span></td>
              <td>{wf.steps?.length || 0}</td>
              <td>{new Date(wf.created_at).toLocaleDateString()}</td>
              <td className="actions">
                <button className="btn btn-secondary" onClick={() => setSelectedWorkflow(wf)}>View</button>
                <button className="btn btn-danger" onClick={() => handleDelete(wf.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
