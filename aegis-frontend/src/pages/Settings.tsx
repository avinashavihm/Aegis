import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { APIKey, AIModel, AIProvider } from '../api/types'

// Provider icons/colors
const PROVIDER_COLORS: Record<string, string> = {
  openai: '#10a37f',
  anthropic: '#d4a574',
  google: '#4285f4',
  groq: '#f55036',
  mistral: '#ff7000',
  cohere: '#39594d',
  together: '#6366f1',
  azure: '#0078d4',
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'api-keys' | 'models' | 'general'>('api-keys')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // API Keys state
  const [apiKeys, setApiKeys] = useState<APIKey[]>([])
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [models, setModels] = useState<AIModel[]>([])
  const [showAddKey, setShowAddKey] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('')
  
  // Form state for new API key
  const [keyForm, setKeyForm] = useState({
    name: '',
    provider: '',
    api_key: '',
    base_url: '',
    organization_id: '',
    is_default: false,
    custom_provider_id: '',
  })

  const loadData = async () => {
    try {
      setLoading(true)
      const [keysData, providersData, modelsData] = await Promise.all([
        api.listAPIKeys(),
        api.listAIProviders(),
        api.listAIModels(),
      ])
      setApiKeys(keysData)
      setProviders(providersData)
      setModels(modelsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const showSuccess = (msg: string) => {
    setSuccess(msg)
    setTimeout(() => setSuccess(''), 3000)
  }

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const providerValue =
        keyForm.provider === 'custom' && keyForm.custom_provider_id
          ? keyForm.custom_provider_id
          : keyForm.provider

      await api.createAPIKey({
        name: keyForm.name,
        provider: providerValue,
        api_key: keyForm.api_key,
        base_url: keyForm.base_url || undefined,
        organization_id: keyForm.organization_id || undefined,
        is_default: keyForm.is_default,
      })
      setKeyForm({
        name: '',
        provider: '',
        api_key: '',
        base_url: '',
        organization_id: '',
        is_default: false,
        custom_provider_id: '',
      })
      setShowAddKey(false)
      loadData()
      showSuccess('API key added successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create API key')
    }
  }

  const handleDeleteKey = async (id: string) => {
    if (!confirm('Delete this API key?')) return
    try {
      await api.deleteAPIKey(id)
      loadData()
      showSuccess('API key deleted')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete API key')
    }
  }

  const handleTestKey = async (id: string) => {
    try {
      const result = await api.testAPIKey(id)
      if (result.valid) {
        showSuccess(`✓ ${result.message}`)
      } else {
        setError(`✗ ${result.message}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test API key')
    }
  }

  const handleSetDefault = async (id: string, provider: string) => {
    try {
      await api.updateAPIKey(id, { is_default: true })
      loadData()
      showSuccess(`Set as default for ${provider}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update API key')
    }
  }

  const getProviderModels = (provider: string) => {
    return models.filter(m => m.provider === provider)
  }

  const getKeysForProvider = (provider: string) => {
    return apiKeys.filter(k => k.provider === provider)
  }

  if (loading) {
    return <div className="container"><p>Loading settings...</p></div>
  }

  return (
    <div className="container">
      <h1>⚙️ Settings</h1>
      
      {error && <div className="error-banner">{error} <button onClick={() => setError('')}>×</button></div>}
      {success && <div className="success-banner">{success}</div>}

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: 24 }}>
        <button 
          className={`tab ${activeTab === 'api-keys' ? 'active' : ''}`}
          onClick={() => setActiveTab('api-keys')}
        >
          🔑 API Keys
        </button>
        <button 
          className={`tab ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
        >
          🤖 AI Models
        </button>
        <button 
          className={`tab ${activeTab === 'general' ? 'active' : ''}`}
          onClick={() => setActiveTab('general')}
        >
          🛠️ General
        </button>
      </div>

      {/* API Keys Tab */}
      {activeTab === 'api-keys' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2>🔑 API Keys</h2>
            <button className="btn btn-primary" onClick={() => setShowAddKey(true)}>
              + Add API Key
            </button>
          </div>
          
          <p style={{ color: '#666', marginBottom: 24 }}>
            Add your API keys to use different AI providers. Your keys are encrypted and stored securely.
          </p>

          {/* Add Key Modal */}
          {showAddKey && (
            <div className="modal-overlay" onClick={() => setShowAddKey(false)}>
              <div className="modal" onClick={e => e.stopPropagation()}>
                <h3>Add API Key</h3>
                <form onSubmit={handleCreateKey}>
                  <div style={{ marginBottom: 16 }}>
                    <label>Provider</label>
                    <select 
                      value={keyForm.provider} 
                      onChange={e => setKeyForm({ ...keyForm, provider: e.target.value })}
                      required
                    >
                      <option value="">Select a provider...</option>
                      {providers.map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  {keyForm.provider && (
                    <>
                      <div style={{ 
                        padding: 12, 
                        background: '#f5f5f5', 
                        borderRadius: 4, 
                        marginBottom: 16,
                        fontSize: '0.9em'
                      }}>
                        <strong>{providers.find(p => p.id === keyForm.provider)?.name}</strong>
                        <p style={{ margin: '4px 0', color: '#666' }}>
                          {providers.find(p => p.id === keyForm.provider)?.description}
                        </p>
                        <a 
                          href={providers.find(p => p.id === keyForm.provider)?.key_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          style={{ color: '#0066cc' }}
                        >
                          Get API Key →
                        </a>
                      </div>

                      {keyForm.provider === 'custom' && (
                        <div style={{ marginBottom: 16 }}>
                          <label>Custom Provider ID</label>
                          <input
                            type="text"
                            placeholder="e.g., firecrawl, weatherapi, crawl4ai"
                            value={keyForm.custom_provider_id}
                            onChange={e => setKeyForm({ ...keyForm, custom_provider_id: e.target.value })}
                            required
                          />
                          <p style={{ color: '#666', fontSize: '0.85em', marginTop: 6 }}>
                            This value will be stored as the provider key (used for selection elsewhere).
                          </p>
                        </div>
                      )}

                      <div style={{ marginBottom: 16 }}>
                        <label>Key Name</label>
                        <input 
                          type="text" 
                          placeholder="e.g., Production Key, Personal Key"
                          value={keyForm.name}
                          onChange={e => setKeyForm({ ...keyForm, name: e.target.value })}
                          required
                        />
                      </div>

                      <div style={{ marginBottom: 16 }}>
                        <label>API Key</label>
                        <input 
                          type="password" 
                          placeholder="sk-..."
                          value={keyForm.api_key}
                          onChange={e => setKeyForm({ ...keyForm, api_key: e.target.value })}
                          required
                        />
                      </div>

                      {keyForm.provider === 'azure' && (
                        <div style={{ marginBottom: 16 }}>
                          <label>Azure Endpoint URL</label>
                          <input 
                            type="url" 
                            placeholder="https://your-resource.openai.azure.com"
                            value={keyForm.base_url}
                            onChange={e => setKeyForm({ ...keyForm, base_url: e.target.value })}
                          />
                        </div>
                      )}

                      {keyForm.provider === 'openai' && (
                        <div style={{ marginBottom: 16 }}>
                          <label>Organization ID (optional)</label>
                          <input 
                            type="text" 
                            placeholder="org-..."
                            value={keyForm.organization_id}
                            onChange={e => setKeyForm({ ...keyForm, organization_id: e.target.value })}
                          />
                        </div>
                      )}

                      <label className="checkbox-label">
                        <input 
                          type="checkbox" 
                          checked={keyForm.is_default}
                          onChange={e => setKeyForm({ ...keyForm, is_default: e.target.checked })}
                        />
                        Set as default for {keyForm.provider}
                      </label>
                    </>
                  )}

                  <div style={{ display: 'flex', gap: 8, marginTop: 24 }}>
                    <button type="submit" className="btn btn-primary" disabled={!keyForm.provider}>
                      Add Key
                    </button>
                    <button type="button" className="btn" onClick={() => setShowAddKey(false)}>
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Providers List */}
          <div className="providers-grid">
            {providers.map(provider => {
              const keys = getKeysForProvider(provider.id)
              const providerModels = getProviderModels(provider.id)
              
              return (
                <div 
                  key={provider.id} 
                  className="provider-card"
                  style={{ borderLeft: `4px solid ${PROVIDER_COLORS[provider.id] || '#999'}` }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h4 style={{ margin: 0, color: PROVIDER_COLORS[provider.id] || '#333' }}>
                        {provider.name}
                      </h4>
                      <p style={{ fontSize: '0.85em', color: '#666', margin: '4px 0' }}>
                        {provider.description}
                      </p>
                    </div>
                    {keys.length > 0 && (
                      <span className="badge badge-success">✓ Configured</span>
                    )}
                  </div>

                  {/* Keys for this provider */}
                  {keys.length > 0 ? (
                    <div style={{ marginTop: 12 }}>
                      {keys.map(key => (
                        <div 
                          key={key.id} 
                          className="api-key-item"
                          style={{ 
                            display: 'flex', 
                            justifyContent: 'space-between', 
                            alignItems: 'center',
                            padding: '8px 0',
                            borderBottom: '1px solid #eee'
                          }}
                        >
                          <div>
                            <strong>{key.name}</strong>
                            {key.is_default && <span className="badge badge-primary" style={{ marginLeft: 8 }}>Default</span>}
                            <div style={{ fontSize: '0.8em', color: '#999' }}>
                              Key: {key.api_key_preview}
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button 
                              className="btn btn-sm"
                              onClick={() => handleTestKey(key.id)}
                              title="Test Key"
                            >
                              🧪
                            </button>
                            {!key.is_default && (
                              <button 
                                className="btn btn-sm"
                                onClick={() => handleSetDefault(key.id, provider.id)}
                                title="Set as Default"
                              >
                                ⭐
                              </button>
                            )}
                            <button 
                              className="btn btn-sm btn-danger"
                              onClick={() => handleDeleteKey(key.id)}
                              title="Delete"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ marginTop: 12 }}>
                      <button 
                        className="btn btn-sm btn-primary"
                        onClick={() => {
                          setKeyForm({ ...keyForm, provider: provider.id })
                          setShowAddKey(true)
                        }}
                      >
                        + Add {provider.name} Key
                      </button>
                    </div>
                  )}

                  {/* Available models */}
                  {providerModels.length > 0 && (
                    <details style={{ marginTop: 12 }}>
                      <summary style={{ cursor: 'pointer', fontSize: '0.85em', color: '#666' }}>
                        {providerModels.length} models available
                      </summary>
                      <div style={{ marginTop: 8, fontSize: '0.85em' }}>
                        {providerModels.slice(0, 5).map(m => (
                          <div key={m.id} style={{ padding: '2px 0', display: 'flex', gap: 8, alignItems: 'center' }}>
                            <code style={{ background: '#f5f5f5', padding: '2px 4px', borderRadius: 2 }}>
                              {m.model_id}
                            </code>
                            {m.supports_vision && <span title="Vision">👁️</span>}
                            {m.supports_tools && <span title="Tools">🔧</span>}
                          </div>
                        ))}
                        {providerModels.length > 5 && (
                          <div style={{ color: '#999' }}>+{providerModels.length - 5} more</div>
                        )}
                      </div>
                    </details>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Models Tab */}
      {activeTab === 'models' && (
        <div className="card">
          <h2>🤖 AI Models</h2>
          <p style={{ color: '#666', marginBottom: 24 }}>
            Browse available AI models. Add an API key for a provider to use their models.
          </p>

          {/* Filter by provider */}
          <div style={{ marginBottom: 16 }}>
            <select 
              value={selectedProvider} 
              onChange={e => setSelectedProvider(e.target.value)}
              style={{ width: 200 }}
            >
              <option value="">All Providers</option>
              {providers.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className="models-grid">
            {models
              .filter(m => !selectedProvider || m.provider === selectedProvider)
              .map(model => (
                <div key={model.id} className="model-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h4 style={{ margin: 0 }}>{model.display_name}</h4>
                      <div style={{ fontSize: '0.8em', color: '#666' }}>
                        <span 
                          style={{ 
                            color: PROVIDER_COLORS[model.provider] || '#666',
                            fontWeight: 500
                          }}
                        >
                          {model.provider}
                        </span>
                        {' · '}
                        <code>{model.model_id}</code>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {model.supports_vision && (
                        <span className="badge" title="Supports Vision">👁️</span>
                      )}
                      {model.supports_tools && (
                        <span className="badge" title="Supports Tools">🔧</span>
                      )}
                    </div>
                  </div>
                  
                  {model.description && (
                    <p style={{ fontSize: '0.85em', color: '#666', margin: '8px 0' }}>
                      {model.description}
                    </p>
                  )}
                  
                  <div style={{ fontSize: '0.8em', color: '#999', marginTop: 8 }}>
                    Context: {(model.context_window / 1000).toFixed(0)}k tokens
                    {model.max_output_tokens && ` · Output: ${(model.max_output_tokens / 1000).toFixed(0)}k`}
                  </div>

                  {/* Check if provider has key */}
                  {!apiKeys.find(k => k.provider === model.provider) && (
                    <div style={{ marginTop: 8 }}>
                      <button 
                        className="btn btn-sm"
                        onClick={() => {
                          setKeyForm({ ...keyForm, provider: model.provider })
                          setShowAddKey(true)
                          setActiveTab('api-keys')
                        }}
                      >
                        + Add API Key to use
                      </button>
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}

      {/* General Tab */}
      {activeTab === 'general' && (
        <div className="card">
          <h2>🛠️ General Settings</h2>
          
          <div style={{ marginBottom: 24 }}>
            <h4>Default Model</h4>
            <p style={{ color: '#666', fontSize: '0.9em' }}>
              Select the default AI model for new agents
            </p>
            <select style={{ width: 300 }}>
              <option value="gemini/gemini-2.0-flash">Gemini 2.0 Flash (Google)</option>
              <option value="openai/gpt-4o">GPT-4o (OpenAI)</option>
              <option value="anthropic/claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Anthropic)</option>
              <option value="groq/llama-3.3-70b-versatile">Llama 3.3 70B (Groq)</option>
            </select>
          </div>

          <div style={{ marginBottom: 24 }}>
            <h4>Agent Defaults</h4>
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              Enable tool usage by default
            </label>
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              Enable streaming responses
            </label>
            <label className="checkbox-label">
              <input type="checkbox" />
              Enable autonomous mode by default
            </label>
          </div>

          <div style={{ marginBottom: 24 }}>
            <h4>Run Limits</h4>
            <div style={{ display: 'flex', gap: 16 }}>
              <div>
                <label>Max Turns per Run</label>
                <input type="number" defaultValue={10} min={1} max={50} style={{ width: 100 }} />
              </div>
              <div>
                <label>Timeout (seconds)</label>
                <input type="number" defaultValue={300} min={30} max={3600} style={{ width: 100 }} />
              </div>
            </div>
          </div>

          <button className="btn btn-primary">Save Settings</button>
        </div>
      )}

      <style>{`
        .tabs {
          display: flex;
          gap: 8px;
          border-bottom: 2px solid #eee;
          padding-bottom: 8px;
        }
        .tab {
          padding: 8px 16px;
          border: none;
          background: none;
          cursor: pointer;
          font-size: 1em;
          color: #666;
          border-radius: 4px 4px 0 0;
        }
        .tab.active {
          color: #0066cc;
          background: #f0f7ff;
          font-weight: 500;
        }
        .tab:hover {
          background: #f5f5f5;
        }
        .providers-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 16px;
        }
        .provider-card {
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 16px;
        }
        .models-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 12px;
        }
        .model-card {
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 12px;
        }
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .modal {
          background: white;
          border-radius: 8px;
          padding: 24px;
          max-width: 500px;
          width: 90%;
          max-height: 90vh;
          overflow-y: auto;
        }
        .badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.75em;
          background: #f0f0f0;
        }
        .badge-success {
          background: #d4edda;
          color: #155724;
        }
        .badge-primary {
          background: #cce5ff;
          color: #004085;
        }
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 8px 0;
          cursor: pointer;
        }
        .btn-sm {
          padding: 4px 8px;
          font-size: 0.85em;
        }
        .success-banner {
          background: #d4edda;
          color: #155724;
          padding: 12px;
          border-radius: 4px;
          margin-bottom: 16px;
        }
        .error-banner {
          background: #f8d7da;
          color: #721c24;
          padding: 12px;
          border-radius: 4px;
          margin-bottom: 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .error-banner button {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 1.2em;
        }
      `}</style>
    </div>
  )
}
