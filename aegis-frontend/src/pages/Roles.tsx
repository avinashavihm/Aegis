import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Role, Policy } from '../api/types'

export default function Roles() {
  const [roles, setRoles] = useState<Role[]>([])
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  // Attach policy
  const [attachRoleId, setAttachRoleId] = useState('')
  const [attachPolicyId, setAttachPolicyId] = useState('')

  const loadData = async () => {
    try {
      const [rolesData, policiesData] = await Promise.all([
        api.listRoles(),
        api.listPolicies()
      ])
      setRoles(rolesData)
      setPolicies(policiesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load roles')
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
      await api.createRole({ name, description })
      setShowCreate(false)
      setName('')
      setDescription('')
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create role')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this role?')) return
    try {
      await api.deleteRole(id)
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete role')
    }
  }

  const handleAttachPolicy = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.attachPolicyToRole(attachRoleId, attachPolicyId)
      setAttachRoleId('')
      setAttachPolicyId('')
      alert('Policy attached successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to attach policy')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Roles</h1>
      {error && <div className="error">{error}</div>}

      <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
        {showCreate ? 'Cancel' : 'Create Role'}
      </button>

      {showCreate && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Create Role</h3>
          <form onSubmit={handleCreate}>
            <input placeholder="Role Name (e.g., my-custom-role)" value={name} onChange={(e) => setName(e.target.value)} required />
            <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
            <button type="submit" className="btn btn-success">Create</button>
          </form>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Attach Policy to Role</h3>
        <form onSubmit={handleAttachPolicy} style={{ display: 'flex', gap: 8 }}>
          <select value={attachRoleId} onChange={(e) => setAttachRoleId(e.target.value)} required style={{ flex: 1 }}>
            <option value="">Select Role</option>
            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <select value={attachPolicyId} onChange={(e) => setAttachPolicyId(e.target.value)} required style={{ flex: 1 }}>
            <option value="">Select Policy</option>
            {policies.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button type="submit" className="btn btn-primary">Attach</button>
        </form>
      </div>

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
          {roles.map(role => (
            <tr key={role.id}>
              <td>{role.name}</td>
              <td>{role.description || '-'}</td>
              <td>{new Date(role.created_at).toLocaleDateString()}</td>
              <td>
                <button className="btn btn-danger" onClick={() => handleDelete(role.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
