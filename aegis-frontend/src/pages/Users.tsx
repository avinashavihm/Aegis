import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { User, Role } from '../api/types'

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')

  // Assign role
  const [assignUserId, setAssignUserId] = useState('')
  const [assignRoleId, setAssignRoleId] = useState('')

  const loadData = async () => {
    try {
      const [usersData, rolesData] = await Promise.all([
        api.listUsers(),
        api.listRoles()
      ])
      setUsers(usersData)
      setRoles(rolesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
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
      await api.createUser({ username, email, password, full_name: fullName })
      setShowCreate(false)
      setUsername('')
      setEmail('')
      setPassword('')
      setFullName('')
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this user?')) return
    try {
      await api.deleteUser(id)
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete user')
    }
  }

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.assignRoleToUser(assignUserId, assignRoleId)
      setAssignUserId('')
      setAssignRoleId('')
      alert('Role assigned successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign role')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Users</h1>
      {error && <div className="error">{error}</div>}

      <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
        {showCreate ? 'Cancel' : 'Create User'}
      </button>

      {showCreate && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Create User</h3>
          <form onSubmit={handleCreate}>
            <input placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <input placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <input placeholder="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            <button type="submit" className="btn btn-success">Create</button>
          </form>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Assign Role to User</h3>
        <form onSubmit={handleAssignRole} style={{ display: 'flex', gap: 8 }}>
          <select value={assignUserId} onChange={(e) => setAssignUserId(e.target.value)} required style={{ flex: 1 }}>
            <option value="">Select User</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
          </select>
          <select value={assignRoleId} onChange={(e) => setAssignRoleId(e.target.value)} required style={{ flex: 1 }}>
            <option value="">Select Role</option>
            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <button type="submit" className="btn btn-primary">Assign</button>
        </form>
      </div>

      <table style={{ marginTop: 16 }}>
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Full Name</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.id}>
              <td>{user.username}</td>
              <td>{user.email}</td>
              <td>{user.full_name || '-'}</td>
              <td>{new Date(user.created_at).toLocaleDateString()}</td>
              <td>
                <button className="btn btn-danger" onClick={() => handleDelete(user.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
