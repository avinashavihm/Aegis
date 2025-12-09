import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Team, User, Role } from '../api/types'

export default function Teams() {
  const [teams, setTeams] = useState<Team[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')

  // Add member
  const [addTeamId, setAddTeamId] = useState('')
  const [addUserId, setAddUserId] = useState('')
  const [addRoleId, setAddRoleId] = useState('')

  const loadData = async () => {
    try {
      const [teamsData, usersData, rolesData] = await Promise.all([
        api.listTeams(),
        api.listUsers(),
        api.listRoles()
      ])
      setTeams(teamsData)
      setUsers(usersData)
      setRoles(rolesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load teams')
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
      await api.createTeam({ name })
      setShowCreate(false)
      setName('')
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create team')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this team?')) return
    try {
      await api.deleteTeam(id)
      loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete team')
    }
  }

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.addTeamMember(addTeamId, addUserId, addRoleId || undefined)
      setAddTeamId('')
      setAddUserId('')
      setAddRoleId('')
      alert('Member added successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add member')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Teams</h1>
      {error && <div className="error">{error}</div>}

      <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
        {showCreate ? 'Cancel' : 'Create Team'}
      </button>

      {showCreate && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Create Team</h3>
          <form onSubmit={handleCreate}>
            <input placeholder="Team Name" value={name} onChange={(e) => setName(e.target.value)} required />
            <button type="submit" className="btn btn-success">Create</button>
          </form>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Add Member to Team</h3>
        <form onSubmit={handleAddMember} style={{ display: 'flex', gap: 8 }}>
          <select value={addTeamId} onChange={(e) => setAddTeamId(e.target.value)} required style={{ flex: 1 }}>
            <option value="">Select Team</option>
            {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <select value={addUserId} onChange={(e) => setAddUserId(e.target.value)} required style={{ flex: 1 }}>
            <option value="">Select User</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
          </select>
          <select value={addRoleId} onChange={(e) => setAddRoleId(e.target.value)} style={{ flex: 1 }}>
            <option value="">Role (optional)</option>
            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <button type="submit" className="btn btn-primary">Add</button>
        </form>
      </div>

      <table style={{ marginTop: 16 }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Owner ID</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {teams.map(team => (
            <tr key={team.id}>
              <td>{team.name}</td>
              <td style={{ fontSize: 12 }}>{team.owner_id}</td>
              <td>{new Date(team.created_at).toLocaleDateString()}</td>
              <td>
                <button className="btn btn-danger" onClick={() => handleDelete(team.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
