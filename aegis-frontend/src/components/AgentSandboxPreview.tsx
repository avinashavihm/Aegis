import { useState, useEffect } from 'react'

interface SandboxPreviewProps {
  projectName: string
  output?: string
  isLoading?: boolean
  onRun?: (task: string) => void
  onStop?: () => void
  isRunning?: boolean
}

export default function AgentSandboxPreview({
  projectName,
  output,
  isLoading = false,
  onRun,
  onStop,
  isRunning = false
}: SandboxPreviewProps) {
  const [showConsole, setShowConsole] = useState(true)
  const [taskInput, setTaskInput] = useState('')
  const [outputLines, setOutputLines] = useState<string[]>([])

  useEffect(() => {
    if (output) {
      setOutputLines(output.split('\n'))
    }
  }, [output])

  const handleRun = () => {
    if (taskInput.trim() && onRun) {
      onRun(taskInput.trim())
      setTaskInput('')
    }
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between bg-gray-800 rounded-lg p-3 border border-gray-700">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400 font-semibold">
            Agent Sandbox: {projectName}
          </span>
          {isRunning && (
            <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">
              Running...
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowConsole(!showConsole)}
            className="p-2 hover:bg-gray-700 rounded transition-colors"
            title="Toggle console"
          >
            💻
          </button>
          {isRunning && onStop && (
            <button
              onClick={onStop}
              className="p-2 hover:bg-red-700 rounded transition-colors text-red-400"
              title="Stop execution"
            >
              ⏹
            </button>
          )}
        </div>
      </div>

      {/* Task Input */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleRun()}
            placeholder="Enter task to execute..."
            className="flex-1 bg-gray-900 text-white px-4 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            disabled={isRunning}
          />
          <button
            onClick={handleRun}
            disabled={!taskInput.trim() || isRunning}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded flex items-center gap-2"
          >
            ▶ Run
          </button>
        </div>
      </div>

      {/* Console Output */}
      {showConsole && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-400">Console Output</span>
            {isLoading && (
              <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          <div className="font-mono text-xs whitespace-pre-wrap text-gray-300 max-h-96 overflow-y-auto bg-gray-900 p-4 rounded">
            {outputLines.length > 0 ? (
              outputLines.map((line, idx) => (
                <div key={idx} className="mb-1">
                  {line || '\u00A0'}
                </div>
              ))
            ) : (
              <div className="text-gray-500">No output yet. Enter a task and click Run.</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
