import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'
import AgentSandboxPreview from '../components/AgentSandboxPreview'
import AgentGenerationProgress, { type GenerationProgressState } from '../components/AgentGenerationProgress'
import ProjectFileTree from '../components/ProjectFileTree'
// Icons replaced with emojis to avoid external dependencies

interface ProjectType {
  name: string
  description: string
  use_case: string
}

type AgentInputType = 'string' | 'number' | 'integer' | 'boolean' | 'string[]' | 'number[]'

interface RegistryAgent {
  name: string
  description: string
  input_config?: {
    inputs: Record<
      string,
      {
        description: string
        type: AgentInputType
        required: boolean
      }
    >
  }
  output_config?: {
    outputName: string
    description: string
    schema?: Record<string, unknown>
  }
  model?: string
  run_config?: { max_time_minutes?: number; max_turns?: number }
}

export default function AgentGenerator() {
  const [projectTypes, setProjectTypes] = useState<Record<string, ProjectType>>({})
  const [selectedType, setSelectedType] = useState('simple')
  const [description, setDescription] = useState('')
  const [projectName, setProjectName] = useState('')
  const [tools] = useState<string[]>([])
  const [capabilities] = useState<string[]>([])
  const [model, setModel] = useState('gpt-4o')
  
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationProgress, setGenerationProgress] = useState<GenerationProgressState>({ stage: null })
  const [generatedProject, setGeneratedProject] = useState<{
    name: string
    files: string[]
    dependencies: string[]
    run_command: string
  } | null>(null)
  const [sandboxType, setSandboxType] = useState<'local' | 'venv' | 'docker' | 'e2b'>('local')
  
  const [projects, setProjects] = useState<string[]>([])
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [projectFiles, setProjectFiles] = useState<string[]>([])
  const [projectStructure, setProjectStructure] = useState('')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState('')
  
  const [sandboxOutput, setSandboxOutput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [_sandboxTask, setSandboxTask] = useState('')
  
  const [isDownloading, setIsDownloading] = useState(false)
  const outputRef = useRef<HTMLDivElement>(null)

  // Agent registry (Gemini-style subagents)
  const [registryAgents, setRegistryAgents] = useState<RegistryAgent[]>([])
  const [registryDirectory, setRegistryDirectory] = useState<string>('')
  const [registryError, setRegistryError] = useState<string | null>(null)
  const [selectedRegistryAgent, setSelectedRegistryAgent] = useState<string>('')
  const [agentInputs, setAgentInputs] = useState<Record<string, string | boolean>>({})
  const [agentOutput, setAgentOutput] = useState('')
  const [isAgentRunning, setIsAgentRunning] = useState(false)
  const [agentRunStatus, setAgentRunStatus] = useState<string>('')
  const [agentModelOverride, setAgentModelOverride] = useState<string>('')
  const [agentMaxTime, setAgentMaxTime] = useState<string>('')
  const [agentMaxTurns, setAgentMaxTurns] = useState<string>('')
  const [availableKeyProviders, setAvailableKeyProviders] = useState<string[]>([])
  const [selectedKeyProviders, setSelectedKeyProviders] = useState<string[]>([])

  // Multi-agent generation
  const [multipleAgents, setMultipleAgents] = useState<Array<{
    description: string
    project_name?: string
    project_type: string
    tools: string[]
    capabilities: string[]
    model: string
  }>>([
    { description: '', project_type: 'simple', tools: [], capabilities: [], model: 'gpt-4o' },
    { description: '', project_type: 'simple', tools: [], capabilities: [], model: 'gpt-4o' }
  ])
  const [workflowName, setWorkflowName] = useState('')
  const [isGeneratingMultiple, setIsGeneratingMultiple] = useState(false)
  const [multipleGenerationResult, setMultipleGenerationResult] = useState<{
    success: boolean
    agents: any[]
    workflow_name?: string
    workflow_created: boolean
    message?: string
    error?: string
  } | null>(null)

  // Agent configuration
  const [configUpdates, setConfigUpdates] = useState<Record<string, any>>({})
  const [isUpdatingConfig, setIsUpdatingConfig] = useState(false)
  const [configUpdateResult, setConfigUpdateResult] = useState<{
    success: boolean
    project_name: string
    files_updated: string[]
    message?: string
    error?: string
  } | null>(null)

  // Workflow management
  const [workflowAgentProjects, setWorkflowAgentProjects] = useState<string[]>([])
  const [workflowDescription, setWorkflowDescription] = useState('')
  const [workflowExecutionMode, setWorkflowExecutionMode] = useState('sequential')
  const [isCreatingWorkflow, setIsCreatingWorkflow] = useState(false)
  const [workflowResult, setWorkflowResult] = useState<{
    success: boolean
    workflow_name: string
    workflow_id?: string
    agent_count: number
    message?: string
    error?: string
  } | null>(null)

  // Docker artifacts
  const [dockerProject, setDockerProject] = useState('')
  const [includeCompose, setIncludeCompose] = useState(true)
  const [isGeneratingDocker, setIsGeneratingDocker] = useState(false)
  const [dockerArtifacts, setDockerArtifacts] = useState<{
    success: boolean
    project_name: string
    artifacts: Array<{
      filename: string
      content: string
      description: string
    }>
    package_structure: string
    message?: string
    error?: string
  } | null>(null)

  // Docker build
  const [buildProject, setBuildProject] = useState('')
  const [customImageName, setCustomImageName] = useState('')
  const [_buildContext, _setBuildContext] = useState('.')
  const [isBuildingImage, setIsBuildingImage] = useState(false)
  const [buildResult, setBuildResult] = useState<{
    success: boolean
    project_name: string
    image_name: string
    build_output?: string
    message?: string
    error?: string
  } | null>(null)

  // Docker deployment
  const [deployProject, setDeployProject] = useState('')
  const [containerName, setContainerName] = useState('')
  const [portMapping, setPortMapping] = useState('')
  const [envFile, setEnvFile] = useState('')
  const [isDeploying, setIsDeploying] = useState(false)
  const [deployResult, setDeployResult] = useState<{
    success: boolean
    project_name: string
    container_name: string
    container_id?: string
    deployment_output?: string
    message?: string
    error?: string
  } | null>(null)

  // Load project types
  useEffect(() => {
    loadProjectTypes()
    loadProjects()
    loadRegistry()
    loadDirectory()
    loadKeyProviders()
  }, [])

  // Load project files when selected
  useEffect(() => {
    if (selectedProject) {
      loadProjectFiles(selectedProject)
    }
  }, [selectedProject])

  // Load file content when selected
  useEffect(() => {
    if (selectedProject && selectedFile) {
      loadFileContent(selectedProject, selectedFile)
    }
  }, [selectedProject, selectedFile])

  // Auto-scroll output
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [sandboxOutput])

  // Reset agent inputs when selection changes
  useEffect(() => {
    const agent = registryAgents.find(a => a.name === selectedRegistryAgent)
    if (agent) {
      const inputs = agent.input_config?.inputs ?? {}
      const defaults: Record<string, string | boolean> = {}
      Object.entries(inputs).forEach(([k, cfg]) => {
        defaults[k] = cfg.type === 'boolean' ? false : ''
      })
      setAgentInputs(defaults)
    }
  }, [selectedRegistryAgent, registryAgents])

  const loadProjectTypes = async () => {
    try {
      const types = await api.listProjectTypes()
      setProjectTypes(types)
    } catch (error: any) {
      alert(`Failed to load project types: ${error.message}`)
    }
  }

  const loadProjects = async () => {
    try {
      const projs = await api.listProjects()
      setProjects(projs)
    } catch (error: any) {
      console.error('Failed to load projects:', error)
    }
  }

  const loadRegistry = async () => {
    try {
      const agents = await api.listRegisteredAgents()
      setRegistryAgents(agents)
      setRegistryError(null)
      if (agents.length > 0 && !selectedRegistryAgent) {
        setSelectedRegistryAgent(agents[0].name)
        const inputs = agents[0].input_config?.inputs ?? {}
        const defaults: Record<string, string | boolean> = {}
        Object.entries(inputs).forEach(([key, cfg]) => {
          defaults[key] = cfg.type === 'boolean' ? false : ''
        })
        setAgentInputs(defaults)
      }
    } catch (error: any) {
      console.warn('Registry unavailable:', error?.message || error)
      setRegistryError('Agent registry unavailable')
    }
  }

  const loadDirectory = async () => {
    try {
      const dir = await api.getAgentDirectory()
      setRegistryDirectory(dir.markdown)
    } catch {
      // optional; ignore if unsupported
    }
  }

  const loadKeyProviders = async () => {
    try {
      // reuse settings API to discover which providers have keys saved
      const keys = await api.listAPIKeys()
      const providers = Array.from(new Set(keys.map(k => k.provider))).filter(Boolean)
      setAvailableKeyProviders(providers)
      setSelectedKeyProviders(providers) // default to all saved keys
    } catch (error: any) {
      console.warn('Unable to load API keys', error?.message || error)
    }
  }

  const loadProjectFiles = async (name: string) => {
    try {
      const data = await api.getProjectFiles(name)
      setProjectFiles(data.files)
      setProjectStructure(data.structure)
      setGeneratedProject({
        name: data.project_name,
        files: data.files,
        dependencies: [],
        run_command: ''
      })
    } catch (error: any) {
      alert(`Failed to load project files: ${error.message}`)
    }
  }

  const loadFileContent = async (projectName: string, filePath: string) => {
    try {
      const data = await api.getFileContent(projectName, filePath)
      setFileContent(data.content)
    } catch (error: any) {
      console.error('Failed to load file content:', error)
      setFileContent('')
    }
  }

  const handleGenerate = async () => {
    if (!description.trim()) {
      alert('Please enter a description for your agent')
      return
    }

    setIsGenerating(true)
    setGenerationProgress({ stage: 'generating', status: 'Starting generation...' })
    setGeneratedProject(null)
    setSandboxOutput('')

    try {
      await api.generateAgentStream(
        {
          description: description.trim(),
          project_name: projectName.trim() || undefined,
          project_type: selectedType,
          tools: tools.length > 0 ? tools : undefined,
          capabilities: capabilities.length > 0 ? capabilities : undefined,
          model: model,
          key_providers: selectedKeyProviders.length ? selectedKeyProviders : undefined,
        },
        (event) => {
          if (event.type === 'status') {
            setGenerationProgress(prev => ({
              ...prev,
              status: event.message,
              message: event.message
            }))
          } else if (event.type === 'file_start') {
            setGenerationProgress(prev => ({
              ...prev,
              stage: 'creating',
              currentFile: event.path,
              message: `Creating ${event.path}...`
            }))
          } else if (event.type === 'file_complete') {
            setGenerationProgress(prev => ({
              ...prev,
              message: `Created ${event.path}`
            }))
          } else if (event.type === 'complete') {
            setGenerationProgress({ stage: 'complete' })
            if (event.project) {
              setGeneratedProject({
                name: event.project.name,
                files: event.project.files.map((f: any) => f.path),
                dependencies: event.project.dependencies || [],
                run_command: `cd ${event.project.name} && python main.py 'your task'`
              })
              setSelectedProject(event.project.name)
              loadProjectFiles(event.project.name)
            }
            setIsGenerating(false)
          } else if (event.type === 'error') {
            alert(`Generation error: ${event.error || event.message}`)
            setIsGenerating(false)
            setGenerationProgress({ stage: null })
          }
        }
      )
    } catch (error: any) {
      alert(`Failed to generate agent: ${error.message}`)
      setIsGenerating(false)
      setGenerationProgress({ stage: null })
    }
  }

  const handleRunInSandbox = async (task: string) => {
    if (!selectedProject) {
      alert('Please select or generate a project first')
      return
    }

    setIsRunning(true)
    setSandboxOutput('')
    setSandboxTask(task)

    try {
      await api.runInSandboxStream(
        {
          project_name: selectedProject,
          task: task,
          sandbox_type: sandboxType,
          timeout_seconds: 300,
          key_providers: selectedKeyProviders.length ? selectedKeyProviders : undefined,
        },
        (event) => {
          if (event.type === 'status') {
            setSandboxOutput(prev => prev + `\n[Status] ${event.message}`)
          } else if (event.type === 'output') {
            setSandboxOutput(prev => prev + event.text)
          } else if (event.type === 'complete') {
            setIsRunning(false)
            if (event.success) {
              setSandboxOutput(prev => prev + `\n\n[Complete] Execution finished with exit code ${event.exit_code}`)
            } else {
              setSandboxOutput(prev => prev + `\n\n[Error] Execution failed`)
            }
          } else if (event.type === 'error') {
            setIsRunning(false)
            setSandboxOutput(prev => prev + `\n\n[Error] ${event.error || event.message}`)
          }
        }
      )
    } catch (error: any) {
      alert(`Failed to run in sandbox: ${error.message}`)
      setIsRunning(false)
    }
  }

  const handleDownload = async () => {
    if (!selectedProject) {
      alert('Please select a project first')
      return
    }

    setIsDownloading(true)
    try {
      const blob = await api.downloadPackage(selectedProject, 'zip', false)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedProject}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error: any) {
      alert(`Failed to download package: ${error.message}`)
    } finally {
      setIsDownloading(false)
    }
  }

  const selectedAgentDef = registryAgents.find(a => a.name === selectedRegistryAgent)

  const parseArrayValue = (value: string, type: AgentInputType) => {
    const parts = value
      .split(',')
      .map(p => p.trim())
      .filter(Boolean)
    if (type === 'number[]') {
      return parts.map(p => Number(p)).filter(v => !Number.isNaN(v))
    }
    return parts
  }

  const buildAgentInputPayload = (): Record<string, unknown> => {
    const payload: Record<string, unknown> = {}
    const inputs = selectedAgentDef?.input_config?.inputs ?? {}
    for (const [key, cfg] of Object.entries(inputs)) {
      const raw = agentInputs[key]
      if ((raw === '' || raw === undefined) && cfg.required) {
        throw new Error(`Missing required input: ${key}`)
      }
      if (raw === '' || raw === undefined) continue
      switch (cfg.type) {
        case 'boolean':
          payload[key] = Boolean(raw)
          break
        case 'number':
        case 'integer':
          payload[key] = Number(raw)
          break
        case 'number[]':
        case 'string[]':
          payload[key] = parseArrayValue(String(raw), cfg.type)
          break
        default:
          payload[key] = raw
      }
    }
    return payload
  }

  const handleRunAgent = async () => {
    if (!selectedRegistryAgent) {
      alert('Select an agent to run')
      return
    }
    if (!selectedAgentDef) return
    try {
      const inputs = buildAgentInputPayload()
      setAgentOutput('')
      setIsAgentRunning(true)
      setAgentRunStatus('Starting...')
      await api.runRegisteredAgentStream(
        {
          agent_name: selectedRegistryAgent,
          inputs,
          model_override: agentModelOverride || undefined,
          max_time_minutes: agentMaxTime ? Number(agentMaxTime) : undefined,
          max_turns: agentMaxTurns ? Number(agentMaxTurns) : undefined,
        },
        (event) => {
          if (event.type === 'status') {
            setAgentRunStatus(event.message)
            setAgentOutput(prev => prev + `\n[Status] ${event.message}`)
          } else if (event.type === 'output') {
            setAgentOutput(prev => prev + (event.text || ''))
          } else if (event.type === 'complete') {
            setIsAgentRunning(false)
            setAgentRunStatus('Complete')
            setAgentOutput(prev => prev + `\n\n[Complete] ${event.message || 'Finished'}`)
          } else if (event.type === 'error') {
            setIsAgentRunning(false)
            setAgentRunStatus('Error')
            setAgentOutput(prev => prev + `\n\n[Error] ${event.error || event.message}`)
          }
        }
      )
    } catch (error: any) {
      alert(error.message || 'Failed to run agent')
      setIsAgentRunning(false)
    }
  }

  const renderInputField = (name: string, cfg: { description: string; type: AgentInputType; required: boolean }) => {
    const value = agentInputs[name] ?? (cfg.type === 'boolean' ? false : '')
    const commonProps = {
      className:
        'w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm',
      id: name,
    }
    if (cfg.type === 'boolean') {
      return (
        <label key={name} className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => setAgentInputs(prev => ({ ...prev, [name]: e.target.checked }))}
          />
          <span>
            {name} {cfg.required ? '*' : ''} — {cfg.description}
          </span>
        </label>
      )
    }

    const placeholder =
      cfg.type === 'string[]' || cfg.type === 'number[]'
        ? 'Comma-separated values'
        : `Enter ${cfg.type}`

    return (
      <div key={name} className="space-y-1">
        <label className="text-sm font-medium" htmlFor={name}>
          {name} {cfg.required ? <span className="text-red-500">*</span> : null}
        </label>
        <input
          type={cfg.type === 'number' || cfg.type === 'integer' ? 'number' : 'text'}
          value={typeof value === 'boolean' ? '' : value}
          placeholder={placeholder}
          onChange={(e) => setAgentInputs(prev => ({ ...prev, [name]: e.target.value }))}
          {...commonProps}
        />
        <p className="text-xs text-gray-500">{cfg.description}</p>
      </div>
    )
  }

  const handleDeleteProject = async (name: string) => {
    if (!confirm(`Are you sure you want to delete project "${name}"?`)) {
      return
    }

    try {
      await api.deleteProject(name)
      await loadProjects()
      if (selectedProject === name) {
        setSelectedProject(null)
        setProjectFiles([])
        setGeneratedProject(null)
      }
    } catch (error: any) {
      alert(`Failed to delete project: ${error.message}`)
    }
  }

  // New handler functions for additional features
  const handleGenerateMultipleAgents = async () => {
    const validAgents = multipleAgents.filter(agent => agent.description.trim())
    if (validAgents.length < 2) {
      alert('Please provide descriptions for at least 2 agents')
      return
    }

    setIsGeneratingMultiple(true)
    setMultipleGenerationResult(null)

    try {
      const result = await api.generateMultipleAgents({
        agents: validAgents.map(agent => ({
          description: agent.description.trim(),
          project_name: agent.project_name?.trim() || undefined,
          project_type: agent.project_type,
          tools: agent.tools.length > 0 ? agent.tools : undefined,
          capabilities: agent.capabilities.length > 0 ? agent.capabilities : undefined,
          model: agent.model,
          key_providers: selectedKeyProviders.length ? selectedKeyProviders : undefined,
        })),
        workflow_name: workflowName.trim() || undefined,
      })

      setMultipleGenerationResult(result)
      if (result.success) {
        await loadProjects() // Refresh project list
      }
    } catch (error: any) {
      alert(`Failed to generate multiple agents: ${error.message}`)
    } finally {
      setIsGeneratingMultiple(false)
    }
  }

  const handleUpdateAgentConfig = async () => {
    if (!selectedProject) {
      alert('Please select a project first')
      return
    }

    if (Object.keys(configUpdates).length === 0) {
      alert('Please provide configuration updates')
      return
    }

    setIsUpdatingConfig(true)
    setConfigUpdateResult(null)

    try {
      const result = await api.updateAgentConfig({
        project_name: selectedProject,
        config_updates: configUpdates,
      })

      setConfigUpdateResult(result)
      if (result.success) {
        // Refresh project files
        await loadProjectFiles(selectedProject)
      }
    } catch (error: any) {
      alert(`Failed to update agent configuration: ${error.message}`)
    } finally {
      setIsUpdatingConfig(false)
    }
  }

  const handleCreateWorkflow = async () => {
    if (workflowAgentProjects.length < 2) {
      alert('Please select at least 2 agent projects for the workflow')
      return
    }

    if (!workflowName.trim()) {
      alert('Please provide a workflow name')
      return
    }

    setIsCreatingWorkflow(true)
    setWorkflowResult(null)

    try {
      const result = await api.createWorkflowFromAgents({
        workflow_name: workflowName.trim(),
        agent_projects: workflowAgentProjects,
        description: workflowDescription.trim() || undefined,
        execution_mode: workflowExecutionMode,
      })

      setWorkflowResult(result)
    } catch (error: any) {
      alert(`Failed to create workflow: ${error.message}`)
    } finally {
      setIsCreatingWorkflow(false)
    }
  }

  const handleGenerateDockerArtifacts = async () => {
    if (!dockerProject) {
      alert('Please select a project')
      return
    }

    setIsGeneratingDocker(true)
    setDockerArtifacts(null)

    try {
      const result = await api.generateDockerArtifacts({
        project_name: dockerProject,
        include_compose: includeCompose,
      })

      setDockerArtifacts(result)
    } catch (error: any) {
      alert(`Failed to generate Docker artifacts: ${error.message}`)
    } finally {
      setIsGeneratingDocker(false)
    }
  }

  const handleBuildDockerImage = async () => {
    if (!buildProject) {
      alert('Please select a project')
      return
    }

    setIsBuildingImage(true)
    setBuildResult(null)

    try {
      const result = await api.buildDockerImage({
        project_name: buildProject,
        image_name: customImageName.trim() || undefined,
        build_context: _buildContext,
      })

      setBuildResult(result)
    } catch (error: any) {
      alert(`Failed to build Docker image: ${error.message}`)
    } finally {
      setIsBuildingImage(false)
    }
  }

  const handleDeployDockerContainer = async () => {
    if (!deployProject) {
      alert('Please select a project')
      return
    }

    setIsDeploying(true)
    setDeployResult(null)

    try {
      const result = await api.deployDockerContainer({
        project_name: deployProject,
        container_name: containerName.trim() || undefined,
        port_mapping: portMapping.trim() || undefined,
        env_file: envFile.trim() || undefined,
      })

      setDeployResult(result)
    } catch (error: any) {
      alert(`Failed to deploy Docker container: ${error.message}`)
    } finally {
      setIsDeploying(false)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <span className="text-3xl">✨</span>
            Superior Agent Generator
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Generate sophisticated multi-file agent projects with AI 
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Generation Form */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Generate New Agent</h2>

            {/* Project Type */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Project Type</label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
              >
                {Object.entries(projectTypes).map(([key, type]) => (
                  <option key={key} value={key}>
                    {type.name}
                  </option>
                ))}
              </select>
              {projectTypes[selectedType] && (
                <p className="text-xs text-gray-500 mt-1">
                  {projectTypes[selectedType].description}
                </p>
              )}
            </div>

            {/* Model Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Model</label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
              >
                <option value="gpt-4o">OpenAI - gpt-4o</option>
                <option value="gpt-4o-mini">OpenAI - gpt-4o-mini</option>
                <option value="gemini/gemini-2.5-pro">Gemini - 2.5 Pro</option>
                <option value="gemini/gemini-2.0-flash">Gemini - 2.0 Flash</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Choose the LLM to use for generation. Ensure the corresponding API key is set in env.
              </p>
            </div>

            {/* Key Providers Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Use API Keys</label>
              {availableKeyProviders.length === 0 ? (
                <p className="text-xs text-gray-500">No saved API keys found. Add keys in Settings.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {availableKeyProviders.map((prov) => {
                    const checked = selectedKeyProviders.includes(prov)
                    return (
                      <label
                        key={prov}
                        className={`text-xs px-3 py-1 rounded border cursor-pointer ${
                          checked ? 'bg-blue-100 border-blue-500 dark:bg-blue-900/30' : 'border-gray-300'
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="mr-2"
                          checked={checked}
                          onChange={(e) => {
                            setSelectedKeyProviders((prev) =>
                              e.target.checked ? [...prev, prov] : prev.filter((p) => p !== prov)
                            )
                          }}
                        />
                        {prov}
                      </label>
                    )
                  })}
                </div>
              )}
              <p className="text-xs text-gray-500 mt-1">
                Selected keys are injected for generation and sandbox runs.
              </p>
            </div>

            {/* Description */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">
                Description <span className="text-red-500">*</span>
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what your agent should do..."
                rows={4}
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
              />
            </div>

            {/* Project Name */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Project Name (optional)</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Auto-generated if empty"
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
              />
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={!description.trim() || isGenerating}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  ✨ Generate Agent
                </>
              )}
            </button>

            {/* Generation Progress */}
            {isGenerating && (
              <div className="mt-4">
                <AgentGenerationProgress state={generationProgress} />
              </div>
            )}
          </div>

          {/* Existing Projects */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Existing Projects</h2>
            {projects.length === 0 ? (
              <p className="text-sm text-gray-500">No projects yet</p>
            ) : (
              <div className="space-y-2">
                {projects.map(project => (
                  <div
                    key={project}
                    className={`flex items-center justify-between p-2 rounded cursor-pointer ${
                      selectedProject === project
                        ? 'bg-blue-100 dark:bg-blue-900/30'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                    onClick={() => setSelectedProject(project)}
                  >
                    <div className="flex items-center gap-2">
                      <span>📁</span>
                      <span className="text-sm">{project}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteProject(project)
                      }}
                      className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Agent Registry */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Registered Agents</h2>
            {registryError ? (
              <p className="text-sm text-gray-500">{registryError}</p>
            ) : registryAgents.length === 0 ? (
              <p className="text-sm text-gray-500">No registered agents found</p>
            ) : (
              <div className="space-y-3">
                {registryAgents.map(agent => (
                  <div
                    key={agent.name}
                    className={`p-3 rounded border ${
                      selectedRegistryAgent === agent.name
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <div className="text-sm font-semibold">{agent.name}</div>
                        <div className="text-xs text-gray-500">{agent.description}</div>
                        <div className="text-[11px] text-gray-500 mt-1">
                          {agent.model ? `Model: ${agent.model} • ` : ''}Inputs:{' '}
                          {Object.keys(agent.input_config?.inputs || {}).length}
                          {agent.run_config?.max_time_minutes
                            ? ` • Max time: ${agent.run_config.max_time_minutes}m`
                            : ''}
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          setSelectedRegistryAgent(agent.name)
                          const inputs = agent.input_config?.inputs ?? {}
                          const defaults: Record<string, string | boolean> = {}
                          Object.entries(inputs).forEach(([k, cfg]) => {
                            defaults[k] = cfg.type === 'boolean' ? false : ''
                          })
                          setAgentInputs(defaults)
                        }}
                        className="px-3 py-1 text-xs bg-blue-600 text-white rounded"
                      >
                        Use
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {registryDirectory && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold mb-2">Agent Directory</h3>
                <div className="text-xs bg-gray-900 text-gray-100 p-3 rounded max-h-48 overflow-y-auto whitespace-pre-wrap">
                  {registryDirectory}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Middle Column - File Tree & Code */}
        <div className="lg:col-span-1 space-y-4">
          {/* File Tree */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Project Files</h2>
            {selectedProject ? (
              <ProjectFileTree
                files={projectFiles}
                structure={projectStructure}
                onFileSelect={setSelectedFile}
                selectedFile={selectedFile}
              />
            ) : (
              <p className="text-sm text-gray-500">Select or generate a project to view files</p>
            )}
          </div>

          {/* File Content */}
          {selectedFile && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">{selectedFile}</h2>
              <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded overflow-auto max-h-96">
                {fileContent || 'Loading...'}
              </pre>
            </div>
          )}
        </div>

        {/* Right Column - Sandbox & Actions */}
        <div className="lg:col-span-1 space-y-4">
          {/* Run Registered Agent */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Run Registered Agent</h2>
            {registryAgents.length === 0 ? (
              <p className="text-sm text-gray-500">No registry available</p>
            ) : (
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="block text-sm font-medium mb-1">Agent</label>
                  <select
                    value={selectedRegistryAgent}
                    onChange={(e) => setSelectedRegistryAgent(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
                  >
                    {registryAgents.map(agent => (
                      <option key={agent.name} value={agent.name}>
                        {agent.name}
                      </option>
                    ))}
                  </select>
                </div>

                {selectedAgentDef && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-1 gap-3">
                      {Object.entries(selectedAgentDef.input_config?.inputs || {}).map(
                        ([name, cfg]) => renderInputField(name, cfg)
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-sm font-medium">Model Override</label>
                        <input
                          type="text"
                          value={agentModelOverride}
                          onChange={(e) => setAgentModelOverride(e.target.value)}
                          className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                          placeholder="optional"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-sm font-medium">Max Time (min)</label>
                          <input
                            type="number"
                            value={agentMaxTime}
                            onChange={(e) => setAgentMaxTime(e.target.value)}
                            className="w-full px-2 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                            placeholder={selectedAgentDef.run_config?.max_time_minutes?.toString() || ''}
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">Max Turns</label>
                          <input
                            type="number"
                            value={agentMaxTurns}
                            onChange={(e) => setAgentMaxTurns(e.target.value)}
                            className="w-full px-2 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                            placeholder={selectedAgentDef.run_config?.max_turns?.toString() || ''}
                          />
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={handleRunAgent}
                      disabled={isAgentRunning}
                      className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white rounded-lg flex items-center justify-center gap-2"
                    >
                      {isAgentRunning ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Running...
                        </>
                      ) : (
                        <>🚀 Run Agent</>
                      )}
                    </button>

                    <div className="text-xs text-gray-500">
                      Agents must call <code>complete_task</code> to finish. Outputs stream below.
                    </div>

                    <div className="bg-gray-900 text-gray-100 p-3 rounded max-h-64 overflow-y-auto text-xs whitespace-pre-wrap">
                      <div className="text-gray-400 mb-2">{agentRunStatus}</div>
                      {agentOutput || 'No output yet.'}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sandbox Preview */}
          {selectedProject && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Sandbox Execution</h2>
              <div className="mb-3">
                <label className="block text-sm font-medium mb-1">Sandbox Type</label>
                <select
                  value={sandboxType}
                  onChange={(e) => setSandboxType(e.target.value as typeof sandboxType)}
                  className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
                >
                  <option value="local">Local (default)</option>
                  <option value="venv">Virtualenv (isolated)</option>
                  <option value="docker">Docker (requires daemon)</option>
                  <option value="e2b">E2B Cloud Sandbox</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  For E2B, set E2B_API_KEY in backend env. Project files are pushed to the sandbox and run remotely.
                </p>
              </div>
              <AgentSandboxPreview
                projectName={selectedProject}
                output={sandboxOutput}
                isLoading={isRunning}
                isRunning={isRunning}
                onRun={handleRunInSandbox}
                onStop={() => setIsRunning(false)}
              />
            </div>
          )}

          {/* Actions */}
          {selectedProject && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Actions</h2>
              <div className="space-y-2">
                <button
                  onClick={handleDownload}
                  disabled={isDownloading}
                  className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg flex items-center justify-center gap-2"
                >
                  {isDownloading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      ⬇️ Download Package
                    </>
                  )}
                </button>
                {generatedProject && (
                  <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm">
                    <p className="font-medium mb-2">Run Command:</p>
                    <code className="text-xs">{generatedProject.run_command}</code>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* New Features - Additional Row */}
        <div className="lg:col-span-3 grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
          {/* Multi-Agent Generation */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">🤖 Multi-Agent Generation</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Generate multiple agents at once and optionally create a workflow to connect them.
            </p>

            {/* Workflow Name */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Workflow Name (optional)</label>
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                placeholder="Name for connecting workflow"
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
              />
            </div>

            {/* Agents */}
            <div className="space-y-3 mb-4">
              {multipleAgents.map((agent, index) => (
                <div key={index} className="border rounded-lg p-3">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium">Agent {index + 1}</span>
                    <button
                      onClick={() => setMultipleAgents(prev => prev.filter((_, i) => i !== index))}
                      className="text-red-500 hover:text-red-700"
                    >
                      ✕
                    </button>
                  </div>
                  <textarea
                    value={agent.description}
                    onChange={(e) => setMultipleAgents(prev =>
                      prev.map((a, i) => i === index ? { ...a, description: e.target.value } : a)
                    )}
                    placeholder="Describe what this agent should do..."
                    rows={2}
                    className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm mb-2"
                  />
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={agent.project_name || ''}
                      onChange={(e) => setMultipleAgents(prev =>
                        prev.map((a, i) => i === index ? { ...a, project_name: e.target.value } : a)
                      )}
                      placeholder="Project name (optional)"
                      className="flex-1 px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                    />
                    <select
                      value={agent.project_type}
                      onChange={(e) => setMultipleAgents(prev =>
                        prev.map((a, i) => i === index ? { ...a, project_type: e.target.value } : a)
                      )}
                      className="px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                    >
                      {Object.entries(projectTypes).map(([key, type]) => (
                        <option key={key} value={key}>
                          {type.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setMultipleAgents(prev => [...prev, {
                  description: '',
                  project_type: 'simple',
                  tools: [],
                  capabilities: [],
                  model: 'gpt-4o'
                }])}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm"
              >
                + Add Agent
              </button>
            </div>

            <button
              onClick={handleGenerateMultipleAgents}
              disabled={isGeneratingMultiple || multipleAgents.filter(a => a.description.trim()).length < 2}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2"
            >
              {isGeneratingMultiple ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                <>🚀 Generate Multiple Agents</>
              )}
            </button>

            {multipleGenerationResult && (
              <div className={`mt-4 p-3 rounded-lg ${multipleGenerationResult.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                <p className="text-sm font-medium">{multipleGenerationResult.message}</p>
                {multipleGenerationResult.workflow_created && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Workflow "{multipleGenerationResult.workflow_name}" created successfully
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Agent Configuration Update */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">⚙️ Agent Configuration</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Update configuration settings for generated agents.
            </p>

            {selectedProject && (
              <>
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2">Selected Project</label>
                  <div className="px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm">
                    {selectedProject}
                  </div>
                </div>

                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2">Configuration Updates (JSON)</label>
                  <textarea
                    value={JSON.stringify(configUpdates, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value)
                        setConfigUpdates(parsed)
                      } catch {
                        // Invalid JSON, keep as string for now
                      }
                    }}
                    placeholder='{"model": "gpt-4", "timeout": 60}'
                    rows={4}
                    className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm font-mono"
                  />
                </div>

                <button
                  onClick={handleUpdateAgentConfig}
                  disabled={isUpdatingConfig || !selectedProject}
                  className="w-full px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2"
                >
                  {isUpdatingConfig ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Updating...
                    </>
                  ) : (
                    <>🔄 Update Configuration</>
                  )}
                </button>

                {configUpdateResult && (
                  <div className={`mt-4 p-3 rounded-lg ${configUpdateResult.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                    <p className="text-sm font-medium">{configUpdateResult.message}</p>
                    {configUpdateResult.files_updated.length > 0 && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        Updated files: {configUpdateResult.files_updated.join(', ')}
                      </p>
                    )}
                  </div>
                )}
              </>
            )}

            {!selectedProject && (
              <p className="text-sm text-gray-500">Select a project to update its configuration</p>
            )}
          </div>

          {/* Workflow Creation */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">🔗 Workflow Creation</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Create workflows that orchestrate multiple agent projects.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Workflow Name</label>
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                placeholder="Enter workflow name"
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Description (optional)</label>
              <textarea
                value={workflowDescription}
                onChange={(e) => setWorkflowDescription(e.target.value)}
                placeholder="Describe what this workflow does..."
                rows={2}
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Execution Mode</label>
              <select
                value={workflowExecutionMode}
                onChange={(e) => setWorkflowExecutionMode(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700"
              >
                <option value="sequential">Sequential</option>
                <option value="parallel">Parallel</option>
              </select>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Select Agent Projects</label>
              <div className="max-h-32 overflow-y-auto border rounded-lg p-2">
                {projects.map(project => (
                  <label key={project} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={workflowAgentProjects.includes(project)}
                      onChange={(e) => {
                        setWorkflowAgentProjects(prev =>
                          e.target.checked
                            ? [...prev, project]
                            : prev.filter(p => p !== project)
                        )
                      }}
                    />
                    {project}
                  </label>
                ))}
              </div>
            </div>

            <button
              onClick={handleCreateWorkflow}
              disabled={isCreatingWorkflow || !workflowName.trim() || workflowAgentProjects.length < 2}
              className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2"
            >
              {isCreatingWorkflow ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Creating...
                </>
              ) : (
                <>🔗 Create Workflow</>
              )}
            </button>

            {workflowResult && (
              <div className={`mt-4 p-3 rounded-lg ${workflowResult.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                <p className="text-sm font-medium">{workflowResult.message}</p>
                {workflowResult.workflow_id && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Workflow ID: {workflowResult.workflow_id}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Docker Operations */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">🐳 Docker Operations</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Generate Docker artifacts, build images, and deploy containers.
            </p>

            <div className="space-y-4">
              {/* Docker Artifacts Generation */}
              <div className="border-b pb-4">
                <h3 className="font-medium mb-2">Generate Docker Artifacts</h3>
                <div className="mb-2">
                  <select
                    value={dockerProject}
                    onChange={(e) => setDockerProject(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                  >
                    <option value="">Select project</option>
                    {projects.map(project => (
                      <option key={project} value={project}>{project}</option>
                    ))}
                  </select>
                </div>
                <label className="flex items-center gap-2 text-sm mb-2">
                  <input
                    type="checkbox"
                    checked={includeCompose}
                    onChange={(e) => setIncludeCompose(e.target.checked)}
                  />
                  Include docker-compose.yml
                </label>
                <button
                  onClick={handleGenerateDockerArtifacts}
                  disabled={isGeneratingDocker || !dockerProject}
                  className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg text-sm flex items-center justify-center gap-1"
                >
                  {isGeneratingDocker ? (
                    <>
                      <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>📦 Generate Artifacts</>
                  )}
                </button>
              </div>

              {/* Docker Build */}
              <div className="border-b pb-4">
                <h3 className="font-medium mb-2">Build Docker Image</h3>
                <div className="mb-2">
                  <select
                    value={buildProject}
                    onChange={(e) => setBuildProject(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                  >
                    <option value="">Select project</option>
                    {projects.map(project => (
                      <option key={project} value={project}>{project}</option>
                    ))}
                  </select>
                </div>
                <input
                  type="text"
                  value={customImageName}
                  onChange={(e) => setCustomImageName(e.target.value)}
                  placeholder="Custom image name (optional)"
                  className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm mb-2"
                />
                <button
                  onClick={handleBuildDockerImage}
                  disabled={isBuildingImage || !buildProject}
                  className="w-full px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg text-sm flex items-center justify-center gap-1"
                >
                  {isBuildingImage ? (
                    <>
                      <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                      Building...
                    </>
                  ) : (
                    <>🏗️ Build Image</>
                  )}
                </button>
              </div>

              {/* Docker Deploy */}
              <div>
                <h3 className="font-medium mb-2">Deploy Container</h3>
                <div className="mb-2">
                  <select
                    value={deployProject}
                    onChange={(e) => setDeployProject(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm"
                  >
                    <option value="">Select project</option>
                    {projects.map(project => (
                      <option key={project} value={project}>{project}</option>
                    ))}
                  </select>
                </div>
                <input
                  type="text"
                  value={containerName}
                  onChange={(e) => setContainerName(e.target.value)}
                  placeholder="Container name (optional)"
                  className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm mb-2"
                />
                <input
                  type="text"
                  value={portMapping}
                  onChange={(e) => setPortMapping(e.target.value)}
                  placeholder="Port mapping (e.g., 8080:80)"
                  className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm mb-2"
                />
                <input
                  type="text"
                  value={envFile}
                  onChange={(e) => setEnvFile(e.target.value)}
                  placeholder="Env file path (optional)"
                  className="w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-sm mb-2"
                />
                <button
                  onClick={handleDeployDockerContainer}
                  disabled={isDeploying || !deployProject}
                  className="w-full px-3 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white rounded-lg text-sm flex items-center justify-center gap-1"
                >
                  {isDeploying ? (
                    <>
                      <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                      Deploying...
                    </>
                  ) : (
                    <>🚀 Deploy Container</>
                  )}
                </button>
              </div>

              {/* Results */}
              {(dockerArtifacts || buildResult || deployResult) && (
                <div className="mt-4 space-y-2">
                  {dockerArtifacts && (
                    <div className={`p-2 rounded-lg text-xs ${dockerArtifacts.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                      <p className="font-medium">{dockerArtifacts.message}</p>
                    </div>
                  )}
                  {buildResult && (
                    <div className={`p-2 rounded-lg text-xs ${buildResult.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                      <p className="font-medium">{buildResult.message}</p>
                      {buildResult.build_output && (
                        <pre className="mt-1 bg-gray-900 text-gray-100 p-2 rounded text-xs overflow-auto max-h-20">
                          {buildResult.build_output}
                        </pre>
                      )}
                    </div>
                  )}
                  {deployResult && (
                    <div className={`p-2 rounded-lg text-xs ${deployResult.success ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                      <p className="font-medium">{deployResult.message}</p>
                      {deployResult.container_id && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Container ID: {deployResult.container_id}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Docker Artifacts Display */}
        {dockerArtifacts && dockerArtifacts.success && (
          <div className="lg:col-span-3 mt-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">📦 Docker Artifacts</h2>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Package Structure */}
                <div>
                  <h3 className="font-medium mb-2">Package Structure</h3>
                  <pre className="text-xs bg-gray-900 text-gray-100 p-4 rounded overflow-auto max-h-64 whitespace-pre-wrap">
                    {dockerArtifacts.package_structure}
                  </pre>
                </div>

                {/* Docker Files */}
                <div>
                  <h3 className="font-medium mb-2">Generated Files</h3>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {dockerArtifacts.artifacts.map((artifact, index) => (
                      <div key={index} className="border rounded-lg p-3">
                        <div className="flex justify-between items-center mb-2">
                          <span className="font-medium text-sm">{artifact.filename}</span>
                          <button
                            onClick={() => navigator.clipboard.writeText(artifact.content)}
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs"
                          >
                            Copy
                          </button>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{artifact.description}</p>
                        <pre className="text-xs bg-gray-900 text-gray-100 p-2 rounded overflow-auto max-h-32 whitespace-pre-wrap">
                          {artifact.content}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
