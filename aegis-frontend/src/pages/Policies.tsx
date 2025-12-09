import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Policy } from '../api/types'

export default function Policies() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [content, setContent] = useState('')

  // View detail
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)

  const loadData = async () => {
    try {
      const data = await api.listPolicies()
      setPolicies(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load policies')
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
      const parsedContent = JSON.parse(content)
      await api.createPolicy({ name, description, content: parsedContent })
      setShowCreate(false)
      setName('')
      setDescription('')
      setContent('')
      loadData()
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON in content field')
      } else {
        setError(err instanceof Error ? err.message : 'Failed to create policy')
      }
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this policy?')) return
    try {
      await api.deletePolicy(id)
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete policy')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  const defaultContent = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "MyPolicy",
      "Effect": "Allow",
      "Action": ["*:read", "*:list"],
      "Resource": ["*"]
    }
  ]
}`

  return (
    <div>
      <h1>Policies</h1>
      {error && <div className="error">{error}</div>}

      <button className="btn btn-primary" onClick={() => { setShowCreate(!showCreate); setContent(defaultContent) }}>
        {showCreate ? 'Cancel' : 'Create Policy'}
      </button>

      {showCreate && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Create Policy</h3>
          <form onSubmit={handleCreate}>
            <input placeholder="Policy Name (e.g., MyCustomPolicy)" value={name} onChange={(e) => setName(e.target.value)} required />
            <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            <label>Content (JSON - AWS IAM style)</label>
            <textarea
              placeholder="Policy content (JSON)"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={10}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
              required
            />
            <button type="submit" className="btn btn-success">Create</button>
          </form>
        </div>
      )}

      {selectedPolicy && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>{selectedPolicy.name}</h3>
          <p>{selectedPolicy.description || 'No description'}</p>
          <pre>{JSON.stringify(selectedPolicy.content, null, 2)}</pre>
          <button className="btn btn-secondary" onClick={() => setSelectedPolicy(null)}>Close</button>
        </div>
      )}

      <table style={{ marginTop: 16 }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {policies.map(policy => (
            <tr key={policy.id}>
              <td>
                <a href="#" onClick={(e) => { e.preventDefault(); setSelectedPolicy(policy) }}>{policy.name}</a>
              </td>
              <td>{policy.description || '-'}</td>
              <td>{new Date(policy.created_at).toLocaleDateString()}</td>
              <td className="actions">
                <button className="btn btn-secondary" onClick={() => setSelectedPolicy(policy)}>View</button>
                <button className="btn btn-danger" onClick={() => handleDelete(policy.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
