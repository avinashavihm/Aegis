import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { logout } = useAuth()

  return (
    <nav>
      <Link to="/">Dashboard</Link>
      <Link to="/users">Users</Link>
      <Link to="/teams">Teams</Link>
      <Link to="/roles">Roles</Link>
      <Link to="/policies">Policies</Link>
      <Link to="/workspaces">Workspaces</Link>
      <Link to="/tools">Tools</Link>
      <Link to="/mcp">MCP</Link>
      <Link to="/agents">Agents</Link>
      <Link to="/agent-generator">✨ Agent Generator</Link>
      <Link to="/runs">Runs</Link>
      <Link to="/settings">⚙️ Settings</Link>
      <span className="nav-right">
        <button className="btn btn-secondary" onClick={logout}>Logout</button>
      </span>
    </nav>
  )
}
