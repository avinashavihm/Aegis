import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Workspace } from '../api/types'

export default function Workspaces() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  // View detail
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null)

  const loadData = async () => {
    try {
      const data = await api.listWorkspaces()
      setWorkspaces(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workspaces')
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
      await api.createWorkspace({ name, description })
      setShowCreate(false)
      setName('')
      setDescription('')
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create workspace')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this workspace?')) return
    try {
      await api.deleteWorkspace(id)
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete workspace')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Workspaces</h1>
      {error && <div className="error">{error}</div>}

      <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
        {showCreate ? 'Cancel' : 'Create Workspace'}
      </button>

      {showCreate && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Create Workspace</h3>
          <form onSubmit={handleCreate}>
            <input placeholder="Workspace Name" value={name} onChange={(e) => setName(e.target.value)} required />
            <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            <button type="submit" className="btn btn-success">Create</button>
          </form>
        </div>
      )}

      {selectedWorkspace && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>{selectedWorkspace.name}</h3>
          <p>{selectedWorkspace.description || 'No description'}</p>
          <p><strong>Owner ID:</strong> {selectedWorkspace.owner_id}</p>
          <pre>{JSON.stringify(selectedWorkspace.content, null, 2)}</pre>
          <button className="btn btn-secondary" onClick={() => setSelectedWorkspace(null)}>Close</button>
        </div>
      )}

      <table style={{ marginTop: 16 }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Owner ID</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {workspaces.map(ws => (
            <tr key={ws.id}>
              <td>
                <a href="#" onClick={(e) => { e.preventDefault(); setSelectedWorkspace(ws) }}>{ws.name}</a>
              </td>
              <td>{ws.description || '-'}</td>
              <td style={{ fontSize: 12 }}>{ws.owner_id}</td>
              <td>{new Date(ws.created_at).toLocaleDateString()}</td>
              <td className="actions">
                <button className="btn btn-secondary" onClick={() => setSelectedWorkspace(ws)}>View</button>
                <button className="btn btn-danger" onClick={() => handleDelete(ws.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
