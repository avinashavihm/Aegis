import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { MCPServer, MCPServerCreate } from '../api/types'

export default function MCPServers() {
  const [servers, setServers] = useState<MCPServer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState<MCPServerCreate>({
    name: '',
    description: '',
    server_type: 'external',
    transport_type: 'stdio',
    endpoint_url: '',
    command: '',
    args: [],
    env_vars: {},
    config: {},
  })

  const load = async () => {
    try {
      const res = await api.listMCPServers()
      setServers(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load MCP servers')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.createMCPServer(form)
      setForm({ ...form, name: '', description: '', endpoint_url: '', command: '' })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create server')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>MCP Servers</h1>
      {error && <div className="error">{error}</div>}

      <div className="card">
        <h3>Registered Servers</h3>
        {servers.length === 0 && <p>No servers yet.</p>}
        {servers.map(s => (
          <div key={s.id} className="list-row">
            <div>
              <strong>{s.name}</strong> <em>({s.transport_type})</em>
              <div>{s.description}</div>
              {s.endpoint_url && <div>Endpoint: {s.endpoint_url}</div>}
            </div>
            <span className={`status-badge status-${s.status || 'inactive'}`}>{s.status || 'inactive'}</span>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Add MCP Server</h3>
        <form onSubmit={handleCreate}>
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <label>Transport</label>
          <select value={form.transport_type} onChange={(e) => setForm({ ...form, transport_type: e.target.value })}>
            <option value="stdio">stdio</option>
            <option value="http">http</option>
            <option value="sse">sse</option>
          </select>
          <input placeholder="Endpoint URL (for http/sse)" value={form.endpoint_url} onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })} />
          <input placeholder="Command (for stdio)" value={form.command} onChange={(e) => setForm({ ...form, command: e.target.value })} />
          <button type="submit" className="btn btn-primary">Save</button>
        </form>
      </div>
    </div>
  )
}
