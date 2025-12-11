import React from 'react'

export interface GenerationProgressState {
  stage: 'generating' | 'analyzing' | 'creating' | 'complete' | null
  status?: string
  files?: Array<{ path: string; completed: boolean }>
  currentFile?: string
  filesCount?: number
  components?: Array<{ name: string; path: string; completed: boolean }>
  message?: string
}

interface GenerationProgressProps {
  state: GenerationProgressState
}

export default function AgentGenerationProgress({ state }: GenerationProgressProps) {
  if (!state.stage || state.stage === 'complete') return null

  const getStageIcon = () => {
    const spinner = <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
    switch (state.stage) {
      case 'generating':
        return <div className="text-blue-500">{spinner}</div>
      case 'analyzing':
        return <div className="text-purple-500">{spinner}</div>
      case 'creating':
        return <div className="w-5 h-5 text-green-500">📄</div>
      default:
        return <div className="text-gray-500">{spinner}</div>
    }
  }

  const getStageText = () => {
    switch (state.stage) {
      case 'generating':
        return 'Generating agent code...'
      case 'analyzing':
        return 'Analyzing requirements...'
      case 'creating':
        return 'Creating project files...'
      default:
        return state.status || 'Processing...'
    }
  }

  return (
    <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 mt-4 border border-gray-200 dark:border-gray-700">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="flex-shrink-0 mt-1">
          {getStageIcon()}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {getStageText()}
          </div>

          {state.message && (
            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              {state.message}
            </div>
          )}

          {/* Files Progress */}
          {state.files && state.files.length > 0 && (
            <div className="mt-3 space-y-1">
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Files: {state.files.filter(f => f.completed).length} / {state.files.length}
              </div>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {state.files.slice(0, 5).map((file, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-xs">
                    {file.completed ? (
                      <span className="text-green-500">✓</span>
                    ) : (
                      <div className="w-3 h-3 border-2 border-gray-300 rounded-full" />
                    )}
                    <span className="text-gray-600 dark:text-gray-400 truncate">
                      {file.path}
                    </span>
                  </div>
                ))}
                {state.files.length > 5 && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 pl-5">
                    +{state.files.length - 5} more files...
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Components Progress */}
          {state.components && state.components.length > 0 && (
            <div className="mt-3 space-y-1">
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Components: {state.components.filter(c => c.completed).length} / {state.components.length}
              </div>
              <div className="flex flex-wrap gap-2">
                {state.components.map((comp, idx) => (
                  <div
                    key={idx}
                    className={`text-xs px-2 py-1 rounded ${
                      comp.completed
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    {comp.name}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Files Count */}
          {state.filesCount !== undefined && (
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Total files: {state.filesCount}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
