import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Agent, Run, AvailableTool, CustomTool, MCPServer, AgentFile, AIModel, AIProvider } from '../api/types'

// Agent templates for quick creation
const AGENT_TEMPLATES = {
  blank: {
    name: 'Custom Agent',
    description: '',
    instructions: 'You are a helpful agent.',
    tools: [],
    tags: [],
  },
  assistant: {
    name: 'General Assistant',
    description: 'A helpful general-purpose assistant',
    instructions: `You are a helpful AI assistant with access to various tools.

## Core Behaviors:
1. **Use Tools Actively**: You have tools available - ALWAYS use them when they can help.
2. **Ask Clarifying Questions**: Before taking action, ask for any missing information.
3. **Think Step-by-Step**: Break complex tasks into smaller steps.
4. **Be Proactive**: Suggest helpful next steps and related information.

## Tool Usage:
- Review available tools before responding
- If a tool can help, USE IT - don't just say you can't do something
- Chain multiple tool calls when needed
- Report tool results clearly`,
    tools: ['search_web', 'fetch_url', 'read_file', 'write_file'],
    tags: ['assistant', 'general'],
  },
  researcher: {
    name: 'Research Assistant',
    description: 'Researches topics using web search and analysis',
    instructions: `You are a research specialist with web search capabilities.

## Your Process:
1. Understand the research question thoroughly
2. Use search_web to find relevant information
3. Use fetch_url to get detailed content from sources
4. Synthesize findings into clear reports
5. Always cite your sources

## Important:
- ASK clarifying questions about the research topic
- Plan your search strategy before executing
- Present findings with source links
- Offer to dig deeper on specific aspects`,
    tools: ['search_web', 'fetch_url', 'fetch_and_extract', 'write_file'],
    tags: ['researcher', 'web', 'analysis'],
  },
  travel: {
    name: 'Travel Planner',
    description: 'Helps plan trips, find flights, hotels, and activities',
    instructions: `You are a travel planning assistant.

## ALWAYS USE YOUR TOOLS - Don't say you can't help!

## Your Process:
1. ASK QUESTIONS FIRST:
   - Travel dates and flexibility
   - Destination preferences
   - Budget range
   - Number of travelers
   - Preferred activities
   - Special requirements

2. SEARCH for information:
   - Use search_web to find flights, hotels, activities
   - Use fetch_url to get details from travel sites

3. PRESENT options:
   - Multiple choices with price ranges
   - Pros and cons for each
   - Your recommendations

## Key Tools:
- search_web: Search for travel options
- fetch_url: Get details from websites
- fetch_and_extract: Summarize travel pages`,
    tools: ['search_web', 'fetch_url', 'fetch_and_extract'],
    tags: ['travel', 'planning'],
  },
  coder: {
    name: 'Code Assistant',
    description: 'Helps write, debug, and explain code',
    instructions: `You are a coding assistant that can write and execute code.

## Capabilities:
- Write code in various languages
- Execute Python code safely
- Read and analyze existing code
- Debug and fix issues

## Guidelines:
- Ask about requirements before writing code
- Write clean, well-documented code
- Test code when possible using execute_python
- Explain your solutions clearly
- Suggest improvements and alternatives`,
    tools: ['execute_python', 'execute_command', 'read_file', 'write_file', 'list_files'],
    tags: ['coder', 'developer', 'programming'],
  },
  data_analyst: {
    name: 'Data Analyst',
    description: 'Analyzes data files and generates insights',
    instructions: `You are a data analysis specialist.

## Your Process:
1. Understand what data the user has
2. Read the data files using read_file
3. Analyze using execute_python with pandas
4. Generate insights and visualizations
5. Present findings clearly

## Capabilities:
- CSV, JSON, Excel file analysis
- Statistical analysis
- Data visualization
- Pattern detection
- Summary reports`,
    tools: ['read_file', 'write_file', 'execute_python', 'list_files', 'search_files'],
    tags: ['data', 'analysis', 'pandas'],
  },
}

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [availableTools, setAvailableTools] = useState<AvailableTool[]>([])
  const [customTools, setCustomTools] = useState<CustomTool[]>([])
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([])
  const [agentFiles, setAgentFiles] = useState<AgentFile[]>([])
  const [aiModels, setAiModels] = useState<AIModel[]>([])
  const [aiProviders, setAiProviders] = useState<AIProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState('blank')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [model, setModel] = useState('gemini/gemini-2.0-flash')
  const [instructions, setInstructions] = useState('You are a helpful agent.')
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [selectedCustomTools, setSelectedCustomTools] = useState<string[]>([])
  const [selectedMcpServers, setSelectedMcpServers] = useState<string[]>([])
  const [tags, setTags] = useState('')
  const [status, setStatus] = useState('active')

  // Run agent - conversation mode
  const [runAgentId, setRunAgentId] = useState('')
  const [inputMessage, setInputMessage] = useState('')
  const [runResult, setRunResult] = useState<Run | null>(null)
  const [runLoading, setRunLoading] = useState(false)
  const [conversationHistory, setConversationHistory] = useState<{role: string, content: string, files?: {name: string, extracted?: string}[]}[]>([])
  const [followUpMessage, setFollowUpMessage] = useState('')
  
  // File attachments for chat
  const [attachedFiles, setAttachedFiles] = useState<{file: File, extracted?: string, uploading?: boolean, error?: string}[]>([])
  const [fileInputKey, setFileInputKey] = useState(0)

  // View/Edit detail
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [editInstructions, setEditInstructions] = useState('')
  const [editTools, setEditTools] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)

  // Tool filter
  const [toolFilter, setToolFilter] = useState('')

  const loadMeta = async () => {
    const [toolsRes, custom, mcp, models, providers] = await Promise.all([
      api.listTools(),
      api.listCustomTools(),
      api.listMCPServers(),
      api.listAIModels().catch(() => []),
      api.listAIProviders().catch(() => []),
    ])
    setAvailableTools(toolsRes.tools)
    setCustomTools(custom)
    setMcpServers(mcp)
    setAiModels(models)
    setAiProviders(providers)
  }

  const loadAgents = async () => {
    const data = await api.listAgents()
    setAgents(data)
  }

  const loadData = async () => {
    try {
      await Promise.all([loadAgents(), loadMeta()])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Apply template when changed
  useEffect(() => {
    const template = AGENT_TEMPLATES[selectedTemplate as keyof typeof AGENT_TEMPLATES]
    if (template && selectedTemplate !== 'blank') {
      setName(template.name)
      setDescription(template.description)
      setInstructions(template.instructions)
      setSelectedTools(template.tools)
      setTags(template.tags.join(', '))
    }
  }, [selectedTemplate])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const tagsList = tags.split(',').map(t => t.trim()).filter(Boolean)
      await api.createAgent({
        name,
        description,
        model,
        instructions,
        tools: selectedTools,
        custom_tool_ids: selectedCustomTools,
        mcp_server_ids: selectedMcpServers,
        tags: tagsList,
        status,
      })
      setShowCreate(false)
      resetForm()
      loadAgents()
      showSuccess('Agent created successfully!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create agent')
    }
  }

  const resetForm = () => {
    setSelectedTemplate('blank')
    setName('')
    setDescription('')
    setModel('gemini/gemini-2.0-flash')
    setInstructions('You are a helpful agent.')
    setSelectedTools([])
    setSelectedCustomTools([])
    setSelectedMcpServers([])
    setTags('')
    setStatus('active')
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this agent?')) return
    try {
      await api.deleteAgent(id)
      loadAgents()
      if (selectedAgent?.id === id) setSelectedAgent(null)
      showSuccess('Agent deleted')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent')
    }
  }

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault()
    setRunLoading(true)
    setRunResult(null)
    
    // Build message with file contents
    const messageWithFiles = buildMessageWithFiles(inputMessage)
    const filesMeta = attachedFiles.filter(f => !f.error).map(f => ({ name: f.file.name, extracted: f.extracted }))
    
    // Start new conversation
    setConversationHistory([{ role: 'user', content: inputMessage, files: filesMeta.length > 0 ? filesMeta : undefined }])
    setAttachedFiles([]) // Clear attachments after sending
    
    try {
      const result = await api.runAgent(runAgentId, {
        input_message: messageWithFiles,
        max_turns: 10,
      })
      setRunResult(result)
      
      // If already completed (synchronous), add response immediately
      if (result.status === 'completed' && result.output) {
        setConversationHistory(prev => [...prev, { role: 'assistant', content: result.output || '' }])
        setRunLoading(false)
      }
      // Otherwise polling will handle it via useEffect
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run agent')
      setRunLoading(false)
    }
  }

  const handleFollowUp = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!followUpMessage.trim() || !runAgentId) return
    
    setRunLoading(true)
    
    // Build message with file contents
    const messageWithFiles = buildMessageWithFiles(followUpMessage)
    const filesMeta = attachedFiles.filter(f => !f.error).map(f => ({ name: f.file.name, extracted: f.extracted }))
    
    const newHistory = [...conversationHistory, { role: 'user', content: followUpMessage, files: filesMeta.length > 0 ? filesMeta : undefined }]
    setConversationHistory(newHistory)
    const msgToSend = messageWithFiles
    setFollowUpMessage('')
    setAttachedFiles([]) // Clear attachments after sending
    
    try {
      // Build context from conversation history
      const contextMessage = newHistory.map(m => 
        `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`
      ).join('\n\n')
      
      const result = await api.runAgent(runAgentId, {
        input_message: msgToSend,
        context_variables: { 
          conversation_history: contextMessage,
          previous_messages: newHistory 
        },
        max_turns: 10,
      })
      setRunResult(result)
      
      // If already completed (synchronous), add response immediately
      if (result.status === 'completed' && result.output) {
        setConversationHistory(prev => [...prev, { role: 'assistant', content: result.output || '' }])
        setRunLoading(false)
      }
      // Otherwise polling will handle it via useEffect
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send follow-up')
      setRunLoading(false)
    }
  }

  const clearConversation = () => {
    setConversationHistory([])
    setRunResult(null)
    setInputMessage('')
    setFollowUpMessage('')
    setAttachedFiles([])
  }

  // Handle file attachment for chat
  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    
    const newFiles: typeof attachedFiles = []
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      newFiles.push({ file, uploading: true })
    }
    
    setAttachedFiles(prev => [...prev, ...newFiles])
    setFileInputKey(prev => prev + 1) // Reset file input
    
    // Upload and extract text for each file
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      try {
        const result = await api.uploadFile(file)
        setAttachedFiles(prev => prev.map(f => 
          f.file.name === file.name && f.uploading
            ? { ...f, uploading: false, extracted: result.extracted_text || undefined }
            : f
        ))
      } catch (err) {
        setAttachedFiles(prev => prev.map(f =>
          f.file.name === file.name && f.uploading
            ? { ...f, uploading: false, error: err instanceof Error ? err.message : 'Upload failed' }
            : f
        ))
      }
    }
  }

  const removeAttachedFile = (fileName: string) => {
    setAttachedFiles(prev => prev.filter(f => f.file.name !== fileName))
  }

  const buildMessageWithFiles = (message: string): string => {
    if (attachedFiles.length === 0) return message
    
    const fileContents = attachedFiles
      .filter(f => f.extracted && !f.error)
      .map(f => `\n\n📎 File: ${f.file.name}\n---\n${f.extracted}\n---`)
      .join('')
    
    return message + fileContents
  }

  const pollRunStatus = async (runId: string) => {
    try {
      const result = await api.getRun(runId)
      setRunResult(result)
      
      // When run completes, add the output to conversation
      if (result.status === 'completed') {
        setRunLoading(false)
        if (result.output) {
          setConversationHistory(prev => {
            // Check if we already have this response (avoid duplicates)
            const lastMsg = prev[prev.length - 1]
            if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content === result.output) {
              return prev
            }
            return [...prev, { role: 'assistant', content: result.output || '' }]
          })
        }
      } else if (result.status === 'failed' || result.status === 'cancelled') {
        setRunLoading(false)
        if (result.error) {
          setConversationHistory(prev => [...prev, { role: 'assistant', content: `❌ Error: ${result.error}` }])
        }
      } else if (result.status === 'pending' || result.status === 'running') {
        setTimeout(() => pollRunStatus(runId), 1000)
      }
    } catch {
      setRunLoading(false)
    }
  }

  useEffect(() => {
    if (runResult && (runResult.status === 'pending' || runResult.status === 'running')) {
      const timeout = setTimeout(() => pollRunStatus(runResult.id), 1000)
      return () => clearTimeout(timeout)
    }
  }, [runResult])

  const toggle = (list: string[], value: string, setter: (v: string[]) => void) => {
    if (list.includes(value)) {
      setter(list.filter(v => v !== value))
    } else {
      setter([...list, value])
    }
  }

  const selectAgent = async (agent: Agent) => {
    setSelectedAgent(agent)
    setEditMode(false)
    setEditInstructions(agent.instructions || '')
    setEditTools(agent.tools || [])
    try {
      const files = await api.listAgentFiles(agent.id)
      setAgentFiles(files)
    } catch {
      setAgentFiles([])
    }
  }

  const handleUpdateAgent = async () => {
    if (!selectedAgent) return
    try {
      await api.updateAgent(selectedAgent.id, {
        instructions: editInstructions,
        tools: editTools,
      })
      await loadAgents()
      setEditMode(false)
      showSuccess('Agent updated!')
      // Refresh selected agent
      const updated = await api.getAgent(selectedAgent.id)
      setSelectedAgent(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update agent')
    }
  }

  const applyTemplateToAgent = async (templateKey: string) => {
    if (!selectedAgent) return
    const template = AGENT_TEMPLATES[templateKey as keyof typeof AGENT_TEMPLATES]
    if (!template || templateKey === 'blank') return
    
    try {
      await api.updateAgent(selectedAgent.id, {
        instructions: template.instructions,
        tools: template.tools,
      })
      setEditInstructions(template.instructions)
      setEditTools(template.tools)
      await loadAgents()
      showSuccess(`Applied "${template.name}" template!`)
      const updated = await api.getAgent(selectedAgent.id)
      setSelectedAgent(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply template')
    }
  }

  const enhanceInstructions = () => {
    if (!selectedAgent) return
    const enhanced = `You are ${selectedAgent.name}, an intelligent AI assistant with access to various tools.

## Core Behaviors:
1. **Use Tools Actively**: You have tools available - ALWAYS use them when they can help. Don't just say you can't do something if a tool might help.
2. **Ask Clarifying Questions**: Before taking action, ask the user for any missing information you need. Don't make assumptions.
3. **Think Step-by-Step**: Break complex tasks into smaller steps and explain your reasoning.
4. **Be Proactive**: Suggest helpful next steps and related information.

## Tool Usage Guidelines:
- Review available tools before responding
- If a tool can help accomplish the task, USE IT
- Chain multiple tool calls when needed
- Report tool results clearly to the user

## Your Specific Role:
${selectedAgent.description || 'Assist users with their tasks.'}

## Previous Instructions:
${editInstructions}
`
    setEditInstructions(enhanced)
  }

  const handleUploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedAgent) return
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await api.uploadAgentFile(selectedAgent.id, file)
      const files = await api.listAgentFiles(selectedAgent.id)
      setAgentFiles(files)
      showSuccess('File uploaded!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const exportAgent = (agent: Agent) => {
    const exportData = {
      apiVersion: 'aegis.io/v1',
      kind: 'Agent',
      metadata: {
        name: agent.name,
        labels: { app: 'aegis', type: 'agent' }
      },
      spec: {
        name: agent.name,
        description: agent.description,
        model: agent.model,
        instructions: agent.instructions,
        tools: agent.tools,
        custom_tool_ids: agent.custom_tool_ids,
        mcp_server_ids: agent.mcp_server_ids,
        tags: agent.tags,
        status: agent.status,
      }
    }
    const yaml = JSON.stringify(exportData, null, 2)
    const blob = new Blob([yaml], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${agent.name.toLowerCase().replace(/\s+/g, '-')}.json`
    a.click()
    URL.revokeObjectURL(url)
    showSuccess(`Exported ${agent.name}`)
  }

  const importAgent = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const spec = data.spec || data
      await api.createAgent({
        name: spec.name + ' (imported)',
        description: spec.description,
        model: spec.model,
        instructions: spec.instructions,
        tools: spec.tools || [],
        custom_tool_ids: spec.custom_tool_ids || [],
        mcp_server_ids: spec.mcp_server_ids || [],
        tags: spec.tags || [],
        status: 'draft',
      })
      loadAgents()
      showSuccess('Agent imported!')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import agent')
    }
    e.target.value = ''
  }

  const showSuccess = (msg: string) => {
    setSuccessMessage(msg)
    setTimeout(() => setSuccessMessage(''), 3000)
  }

  const filteredTools = availableTools.filter(t =>
    toolFilter === '' || t.name.toLowerCase().includes(toolFilter.toLowerCase()) ||
    (t.category && t.category.toLowerCase().includes(toolFilter.toLowerCase()))
  )

  // Recommend tools based on what the agent might need
  const getRecommendedTools = () => {
    const desc = (description + ' ' + instructions).toLowerCase()
    const recommended: string[] = []
    if (desc.includes('search') || desc.includes('web') || desc.includes('internet') || desc.includes('travel')) {
      recommended.push('search_web', 'fetch_url', 'fetch_and_extract')
    }
    if (desc.includes('code') || desc.includes('python') || desc.includes('script')) {
      recommended.push('execute_python', 'execute_command')
    }
    if (desc.includes('file') || desc.includes('read') || desc.includes('write') || desc.includes('data')) {
      recommended.push('read_file', 'write_file', 'list_files')
    }
    return [...new Set(recommended)]
  }

  if (loading) return <div className="loading">Loading...</div>

  return (
    <div>
      <h1>Agents</h1>
      {error && <div className="error" onClick={() => setError('')}>{error} (click to dismiss)</div>}
      {successMessage && <div className="success">{successMessage}</div>}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ Create Agent'}
        </button>
        <label className="btn" style={{ cursor: 'pointer' }}>
          📥 Import
          <input type="file" accept=".json,.yaml,.yml" onChange={importAgent} style={{ display: 'none' }} />
        </label>
      </div>

      {showCreate && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Create Agent</h3>
          
          {/* Template Selection */}
          <div style={{ marginBottom: 16 }}>
            <label><strong>Start from template:</strong></label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
              {Object.entries(AGENT_TEMPLATES).map(([key, _template]) => (
                <button
                  key={key}
                  type="button"
                  className={`btn ${selectedTemplate === key ? 'btn-primary' : ''}`}
                  onClick={() => setSelectedTemplate(key)}
                  style={{ textTransform: 'capitalize' }}
                >
                  {key === 'blank' ? '📝 Blank' : 
                   key === 'assistant' ? '🤖 Assistant' :
                   key === 'researcher' ? '🔍 Researcher' :
                   key === 'travel' ? '✈️ Travel' :
                   key === 'coder' ? '💻 Coder' :
                   key === 'data_analyst' ? '📊 Data Analyst' : key}
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleCreate}>
            <input 
              placeholder="Agent Name" 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
              required 
            />
            <textarea 
              placeholder="Description (what does this agent do?)" 
              value={description} 
              onChange={(e) => setDescription(e.target.value)} 
              rows={2} 
            />
            <div style={{ marginBottom: 12 }}>
              <label><strong>AI Model</strong></label>
              {aiModels.length > 0 ? (
                <select value={model} onChange={(e) => setModel(e.target.value)}>
                  {aiProviders.map(provider => {
                    const providerModels = aiModels.filter(m => m.provider === provider.id)
                    if (providerModels.length === 0) return null
                    return (
                      <optgroup key={provider.id} label={provider.name}>
                        {providerModels.map(m => (
                          <option key={m.id} value={`${m.provider}/${m.model_id}`}>
                            {m.display_name} {m.supports_vision ? '👁️' : ''} {m.supports_tools ? '🔧' : ''}
                          </option>
                        ))}
                      </optgroup>
                    )
                  })}
                </select>
              ) : (
                <input 
                  placeholder="Model (e.g., gemini/gemini-2.0-flash)" 
                  value={model} 
                  onChange={(e) => setModel(e.target.value)} 
                />
              )}
              <div style={{ fontSize: '0.8em', color: '#666', marginTop: 4 }}>
                💡 Add API keys in <a href="/settings">Settings</a> to use different providers
              </div>
            </div>
            
            <div style={{ marginBottom: 12 }}>
              <label><strong>Instructions</strong> (tell the agent how to behave)</label>
              <textarea 
                placeholder="Instructions" 
                value={instructions} 
                onChange={(e) => setInstructions(e.target.value)} 
                rows={8}
                style={{ fontFamily: 'monospace', fontSize: '0.9em' }}
              />
              <div style={{ fontSize: '0.8em', color: '#666' }}>
                Tip: Include guidance on using tools, asking questions, and handling requests.
              </div>
            </div>

            {/* Tool Selection with Search */}
            <div className="pill-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>Tools ({selectedTools.length} selected)</strong>
                <input
                  type="text"
                  placeholder="Filter tools..."
                  value={toolFilter}
                  onChange={(e) => setToolFilter(e.target.value)}
                  style={{ width: 150, padding: '4px 8px', fontSize: '0.9em' }}
                />
              </div>
              
              {/* Recommended tools */}
              {getRecommendedTools().length > 0 && (
                <div style={{ marginTop: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: '0.8em', color: '#666' }}>Recommended: </span>
                  {getRecommendedTools().map(tool => (
                    <button
                      key={tool}
                      type="button"
                      className="btn"
                      style={{ fontSize: '0.8em', padding: '2px 8px', marginRight: 4 }}
                      onClick={() => !selectedTools.includes(tool) && setSelectedTools([...selectedTools, tool])}
                      disabled={selectedTools.includes(tool)}
                    >
                      + {tool}
                    </button>
                  ))}
                </div>
              )}
              
              <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #ddd', padding: 8, borderRadius: 4 }}>
                {filteredTools.map(t => (
                  <label key={t.name} className="pill" title={t.description}>
                    <input
                      type="checkbox"
                      checked={selectedTools.includes(t.name)}
                      onChange={() => toggle(selectedTools, t.name, setSelectedTools)}
                    />
                    {t.name}
                    <span style={{ fontSize: '0.7em', color: '#999', marginLeft: 4 }}>
                      ({t.category || 'general'})
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="pill-group">
              <strong>Custom Tools</strong>
              {customTools.length === 0 && <div style={{ color: '#666' }}>No custom tools yet.</div>}
              {customTools.map(ct => (
                <label key={ct.id} className="pill">
                  <input
                    type="checkbox"
                    checked={selectedCustomTools.includes(ct.id)}
                    onChange={() => toggle(selectedCustomTools, ct.id, setSelectedCustomTools)}
                  />
                  {ct.name}
                </label>
              ))}
            </div>

            <div className="pill-group">
              <strong>MCP Servers</strong>
              {mcpServers.length === 0 && <div style={{ color: '#666' }}>No MCP servers yet.</div>}
              {mcpServers.map(ms => (
                <label key={ms.id} className="pill">
                  <input
                    type="checkbox"
                    checked={selectedMcpServers.includes(ms.id)}
                    onChange={() => toggle(selectedMcpServers, ms.id, setSelectedMcpServers)}
                  />
                  {ms.name}
                </label>
              ))}
            </div>

            <input placeholder="Tags (comma-separated)" value={tags} onChange={(e) => setTags(e.target.value)} />
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <button type="submit" className="btn btn-success">Create Agent</button>
          </form>
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>💬 Run Agent</h3>
          {conversationHistory.length > 0 && (
            <button className="btn" onClick={clearConversation} style={{ fontSize: '0.8em' }}>
              🔄 New Conversation
            </button>
          )}
        </div>
        
        {conversationHistory.length === 0 ? (
          // Initial message form
          <form onSubmit={handleRun}>
            <select value={runAgentId} onChange={(e) => { setRunAgentId(e.target.value); clearConversation(); }} required>
              <option value="">Select Agent</option>
              {agents.filter(a => a.status === 'active').map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
            <textarea
              placeholder="What would you like the agent to do?"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              rows={3}
              required
            />
            
            {/* File attachments */}
            <div style={{ marginBottom: 12 }}>
              <label className="btn" style={{ cursor: 'pointer', marginRight: 8 }}>
                📎 Attach Files
                <input 
                  key={fileInputKey}
                  type="file" 
                  multiple 
                  accept=".pdf,.doc,.docx,.txt,.csv,.xls,.xlsx,.json,.png,.jpg,.jpeg,.gif,.webp"
                  onChange={handleFileAttach}
                  style={{ display: 'none' }} 
                />
              </label>
              <span style={{ fontSize: '0.8em', color: '#666' }}>
                PDF, DOCX, CSV, Excel, TXT, JSON, Images
              </span>
              
              {/* Show attached files */}
              {attachedFiles.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {attachedFiles.map((f, idx) => (
                    <div 
                      key={idx}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '4px 8px',
                        background: f.error ? '#ffebee' : f.uploading ? '#fff3e0' : '#e8f5e9',
                        borderRadius: 4,
                        fontSize: '0.85em'
                      }}
                    >
                      {f.uploading ? '⏳' : f.error ? '❌' : '📄'} {f.file.name}
                      {f.extracted && <span style={{ color: '#4caf50' }}>✓</span>}
                      <button 
                        type="button"
                        onClick={() => removeAttachedFile(f.file.name)}
                        style={{ 
                          background: 'none', 
                          border: 'none', 
                          cursor: 'pointer',
                          padding: '0 4px',
                          color: '#999'
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <button type="submit" className="btn btn-primary" disabled={runLoading || attachedFiles.some(f => f.uploading)}>
              {runLoading ? '⏳ Running...' : attachedFiles.some(f => f.uploading) ? '⏳ Uploading files...' : '▶️ Start Conversation'}
            </button>
          </form>
        ) : (
          // Conversation view
          <div>
            {/* Conversation History */}
            <div style={{ 
              maxHeight: 400, 
              overflowY: 'auto', 
              border: '1px solid #ddd', 
              borderRadius: 8, 
              padding: 16,
              marginBottom: 16,
              background: '#fafafa'
            }}>
              {conversationHistory.map((msg, idx) => (
                <div 
                  key={idx} 
                  style={{ 
                    marginBottom: 12,
                    padding: 12,
                    borderRadius: 8,
                    background: msg.role === 'user' ? '#e3f2fd' : '#ffffff',
                    border: msg.role === 'user' ? '1px solid #90caf9' : '1px solid #e0e0e0',
                    marginLeft: msg.role === 'user' ? 40 : 0,
                    marginRight: msg.role === 'assistant' ? 40 : 0,
                  }}
                >
                  <div style={{ 
                    fontSize: '0.75em', 
                    color: '#666', 
                    marginBottom: 4,
                    fontWeight: 'bold'
                  }}>
                    {msg.role === 'user' ? '👤 You' : '🤖 Agent'}
                  </div>
                  {/* Show attached files */}
                  {msg.files && msg.files.length > 0 && (
                    <div style={{ marginBottom: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {msg.files.map((f, fidx) => (
                        <span 
                          key={fidx}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 4,
                            padding: '2px 6px',
                            background: '#e8f5e9',
                            borderRadius: 4,
                            fontSize: '0.8em'
                          }}
                        >
                          📎 {f.name}
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                </div>
              ))}
              {runLoading && (
                <div style={{ textAlign: 'center', padding: 16, color: '#666' }}>
                  ⏳ Agent is thinking...
                </div>
              )}
            </div>

            {/* Follow-up input */}
            <form onSubmit={handleFollowUp}>
              {/* Show attached files for follow-up */}
              {attachedFiles.length > 0 && (
                <div style={{ marginBottom: 8, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {attachedFiles.map((f, idx) => (
                    <div 
                      key={idx}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                        padding: '4px 8px',
                        background: f.error ? '#ffebee' : f.uploading ? '#fff3e0' : '#e8f5e9',
                        borderRadius: 4,
                        fontSize: '0.85em'
                      }}
                    >
                      {f.uploading ? '⏳' : f.error ? '❌' : '📄'} {f.file.name}
                      {f.extracted && <span style={{ color: '#4caf50' }}>✓</span>}
                      <button 
                        type="button"
                        onClick={() => removeAttachedFile(f.file.name)}
                        style={{ 
                          background: 'none', 
                          border: 'none', 
                          cursor: 'pointer',
                          padding: '0 4px',
                          color: '#999'
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div style={{ display: 'flex', gap: 8 }}>
                <label style={{ 
                  cursor: 'pointer', 
                  display: 'flex', 
                  alignItems: 'center',
                  padding: '8px',
                  color: '#666',
                  borderRadius: 4,
                  border: '1px solid #ddd',
                  alignSelf: 'flex-end'
                }}>
                  📎
                  <input 
                    key={fileInputKey}
                    type="file" 
                    multiple 
                    accept=".pdf,.doc,.docx,.txt,.csv,.xls,.xlsx,.json,.png,.jpg,.jpeg,.gif,.webp"
                    onChange={handleFileAttach}
                    style={{ display: 'none' }} 
                    disabled={runLoading}
                  />
                </label>
                <textarea
                  placeholder="Reply to the agent... (You can attach files with 📎)"
                  value={followUpMessage}
                  onChange={(e) => setFollowUpMessage(e.target.value)}
                  rows={2}
                  style={{ flex: 1, marginBottom: 0 }}
                  disabled={runLoading}
                />
                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  disabled={runLoading || (!followUpMessage.trim() && attachedFiles.length === 0) || attachedFiles.some(f => f.uploading)}
                  style={{ height: 'fit-content', alignSelf: 'flex-end' }}
                >
                  {runLoading ? '⏳' : attachedFiles.some(f => f.uploading) ? '⏳' : '📤 Send'}
                </button>
              </div>
            </form>

            {/* Run details (collapsible) */}
            {runResult && (
              <details style={{ marginTop: 16 }}>
                <summary style={{ cursor: 'pointer', color: '#666' }}>
                  Run Details (ID: {runResult.id.slice(0, 8)}...)
                </summary>
                <div style={{ marginTop: 8, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                  <p><strong>Status:</strong> <span className={`status-badge status-${runResult.status}`}>{runResult.status}</span></p>
                  {runResult.error && (
                    <div className="error">
                      <strong>Error:</strong> {runResult.error}
                    </div>
                  )}
                  {runResult.tool_calls && runResult.tool_calls.length > 0 && (
                    <div>
                      <strong>🔧 Tool Calls ({runResult.tool_calls.length}):</strong>
                      <pre style={{ background: '#e8f4e8', padding: 8, borderRadius: 4, fontSize: '0.8em', marginTop: 4 }}>
                        {JSON.stringify(runResult.tool_calls, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Agents ({agents.length})</h3>
        {agents.length === 0 && <p style={{ color: '#666' }}>No agents yet. Create one above!</p>}
        {agents.map(a => (
          <div key={a.id} className="list-row">
            <div>
              <strong>{a.name}</strong> <span className={`status-badge status-${a.status}`}>{a.status}</span>
              <div style={{ color: '#666', fontSize: '0.9em' }}>{a.description || 'No description'}</div>
              <div style={{ fontSize: '0.8em', color: '#999' }}>
                Tools: {(a.tools || []).length} | Model: {a.model}
              </div>
            </div>
            <div className="row-actions">
              <button className="btn" onClick={() => selectAgent(a)}>View</button>
              <button className="btn" onClick={() => exportAgent(a)} title="Export to JSON">📤</button>
              <button className="btn btn-danger" onClick={() => handleDelete(a.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>

      {selectedAgent && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>{selectedAgent.name}</h3>
            <div>
              <button className="btn" onClick={() => setEditMode(!editMode)}>
                {editMode ? '❌ Cancel' : '✏️ Edit'}
              </button>
              <button className="btn" onClick={() => exportAgent(selectedAgent)} style={{ marginLeft: 8 }}>
                📤 Export
              </button>
            </div>
          </div>
          
          <p>{selectedAgent.description || 'No description'}</p>
          <p><strong>Model:</strong> {selectedAgent.model}</p>
          <p><strong>Status:</strong> <span className={`status-badge status-${selectedAgent.status}`}>{selectedAgent.status}</span></p>
          
          {/* Quick template apply buttons */}
          <div style={{ marginBottom: 12, padding: 8, background: '#f0f7ff', borderRadius: 4 }}>
            <span style={{ fontSize: '0.85em', marginRight: 8 }}>🔧 Quick Fix - Apply Template:</span>
            {Object.entries(AGENT_TEMPLATES).filter(([k]) => k !== 'blank').map(([key, tmpl]) => (
              <button 
                key={key}
                className="btn"
                style={{ fontSize: '0.75em', padding: '4px 8px', marginLeft: 4 }}
                onClick={() => applyTemplateToAgent(key)}
              >
                {tmpl.name}
              </button>
            ))}
          </div>
          
          {editMode ? (
            <div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>Instructions:</strong>
                  <button type="button" className="btn" onClick={enhanceInstructions} style={{ fontSize: '0.8em' }}>
                    ✨ Enhance Instructions
                  </button>
                </div>
                <textarea
                  value={editInstructions}
                  onChange={(e) => setEditInstructions(e.target.value)}
                  rows={12}
                  style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.9em' }}
                />
              </div>
              
              <div style={{ marginBottom: 12 }}>
                <strong>Tools ({editTools.length} selected):</strong>
                <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid #ddd', padding: 8, borderRadius: 4, marginTop: 8 }}>
                  {availableTools.map(t => (
                    <label key={t.name} className="pill">
                      <input
                        type="checkbox"
                        checked={editTools.includes(t.name)}
                        onChange={() => toggle(editTools, t.name, setEditTools)}
                      />
                      {t.name}
                    </label>
                  ))}
                </div>
              </div>
              
              <button className="btn btn-success" onClick={handleUpdateAgent}>
                💾 Save Changes
              </button>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 12 }}>
                <strong>Instructions:</strong>
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, whiteSpace: 'pre-wrap', fontSize: '0.9em' }}>
                  {selectedAgent.instructions || 'No instructions'}
                </pre>
              </div>
              
              <p><strong>Tools:</strong> {(selectedAgent.tools || []).join(', ') || 'None'}</p>
              <p><strong>Custom Tools:</strong> {(selectedAgent.custom_tool_ids || []).length}</p>
              <p><strong>MCP Servers:</strong> {(selectedAgent.mcp_server_ids || []).length}</p>
              <p><strong>Tags:</strong> {(selectedAgent.tags || []).join(', ') || 'None'}</p>
            </>
          )}

          <div style={{ marginTop: 16, borderTop: '1px solid #ddd', paddingTop: 16 }}>
            <h4>📁 Files</h4>
            <input type="file" onChange={handleUploadFile} disabled={uploading} />
            {uploading && <span> Uploading...</span>}
            {agentFiles.length === 0 && <p style={{ color: '#666' }}>No files uploaded.</p>}
            {agentFiles.map(f => (
              <div key={f.id} style={{ padding: '4px 0' }}>
                📄 {f.file_name} ({Math.round((f.file_size || 0)/1024)} KB)
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{`
        .success {
          background: #d4edda;
          color: #155724;
          padding: 12px;
          border-radius: 4px;
          margin-bottom: 16px;
        }
        .pill-group {
          margin: 12px 0;
        }
        .pill {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          margin: 2px;
          background: #f0f0f0;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9em;
        }
        .pill:hover {
          background: #e0e0e0;
        }
        .pill input[type="checkbox"] {
          margin: 0;
        }
      `}</style>
    </div>
  )
}
