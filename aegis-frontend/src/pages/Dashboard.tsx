import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { User } from '../api/types'

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    api.getMe().then(setUser).catch(() => {})
  }, [])

  return (
    <div>
      <h1>Aegis Dashboard</h1>
      {user && (
        <div className="card">
          <p>Welcome, <strong>{user.full_name || user.username}</strong>!</p>
          <p>Email: {user.email}</p>
        </div>
      )}

      <h2>Resources</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <Link to="/users" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Users</h3>
          <p>Manage system users</p>
        </Link>
        <Link to="/teams" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Teams</h3>
          <p>Manage teams and members</p>
        </Link>
        <Link to="/roles" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Roles</h3>
          <p>Manage roles and permissions</p>
        </Link>
        <Link to="/policies" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Policies</h3>
          <p>Manage access policies</p>
        </Link>
        <Link to="/workspaces" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Workspaces</h3>
          <p>Manage workspaces</p>
        </Link>
        <Link to="/agents" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Agents</h3>
          <p>Manage AI agents</p>
        </Link>
        <Link to="/workflows" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Workflows</h3>
          <p>Manage workflows</p>
        </Link>
        <Link to="/runs" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3>Runs</h3>
          <p>View execution history</p>
        </Link>
      </div>
    </div>
  )
}
