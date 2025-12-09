import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { AvailableTool, CustomTool, CustomToolCreate } from '../api/types'

export default function Tools() {
  const [tools, setTools] = useState<AvailableTool[]>([])
  const [customTools, setCustomTools] = useState<CustomTool[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [form, setForm] = useState<Omit<CustomToolCreate, 'definition'> & { definition: Record<string, unknown> | string }>({
    name: '',
    description: '',
    definition_type: 'json',
    definition: '{}',
    code_content: '',
    parameters: [],
    return_type: 'any',
    config: {},
  })

  const load = async () => {
    try {
      const res = await api.listTools()
      setTools(res.tools)
      const custom = await api.listCustomTools()
      setCustomTools(custom)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tools')
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
      let definition: Record<string, unknown> = {}
      if (form.definition_type === 'json' && typeof form.definition === 'string') {
        try {
          definition = JSON.parse(form.definition)
        } catch {
          setError('Definition must be valid JSON')
          return
        }
      } else if (typeof form.definition === 'object') {
        definition = form.definition
      }
      
      const payload: CustomToolCreate = {
        name: form.name,
        description: form.description,
        definition_type: form.definition_type,
        definition,
        code_content: form.code_content,
        parameters: form.parameters,
        return_type: form.return_type,
        config: form.config,
      }
      await api.createCustomTool(payload)
      setForm({ ...form, name: '', description: '', code_content: '', definition: '{}' })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create custom tool')
    }
  }

  const handleDelete = async (toolId: string) => {
    if (!confirm('Delete custom tool?')) return
    try {
      await api.deleteCustomTool(toolId)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete tool')
    }
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Tools</h1>
      {error && <div className="error">{error}</div>}

      <div className="card">
        <h3>Available Tools</h3>
        <ul>
          {tools.map(t => (
            <li key={t.name}>
              <strong>{t.name}</strong> <em>({t.category})</em> - {t.description}
            </li>
          ))}
        </ul>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Custom Tools</h3>
        {customTools.length === 0 && <p>No custom tools yet.</p>}
        {customTools.map(ct => (
          <div key={ct.id} className="list-row">
            <div>
              <strong>{ct.name}</strong> <em>({ct.definition_type})</em>
              <div>{ct.description}</div>
            </div>
            <button className="btn btn-danger" onClick={() => handleDelete(ct.id)}>Delete</button>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Create Custom Tool</h3>
        <form onSubmit={handleCreate}>
          <input
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <textarea
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <label>Definition Type</label>
          <select
            value={form.definition_type}
            onChange={(e) => setForm({ ...form, definition_type: e.target.value })}
          >
            <option value="json">JSON</option>
            <option value="python">Python</option>
          </select>
          {form.definition_type === 'json' ? (
            <textarea
              placeholder='JSON definition (e.g., {"action_type":"http","url":"https://example.com"})'
              value={typeof form.definition === 'string' ? form.definition : JSON.stringify(form.definition || {}, null, 2)}
              onChange={(e) => setForm({ ...form, definition: e.target.value })}
              rows={4}
            />
          ) : (
            <textarea
              placeholder="Python code (define main(**kwargs))"
              value={form.code_content}
              onChange={(e) => setForm({ ...form, code_content: e.target.value })}
              rows={6}
            />
          )}
          <button type="submit" className="btn btn-primary">Save Tool</button>
        </form>
      </div>
    </div>
  )
}
