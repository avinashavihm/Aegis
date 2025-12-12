import { useState } from 'react'

interface FileNode {
  name: string
  path: string
  type: 'file' | 'folder'
  children?: FileNode[]
}

interface ProjectFileTreeProps {
  files: string[]
  structure?: string
  onFileSelect?: (path: string) => void
  selectedFile?: string | null
}

export default function ProjectFileTree({
  files,
  structure: _structure,
  onFileSelect,
  selectedFile
}: ProjectFileTreeProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())

  // Build tree structure from file paths
  const buildTree = (): FileNode[] => {
    const tree: Record<string, FileNode> = {}

    files.forEach(filePath => {
      const parts = filePath.split('/')
      let currentPath = ''
      
      parts.forEach((part, idx) => {
        const isFile = idx === parts.length - 1
        const fullPath = currentPath ? `${currentPath}/${part}` : part
        
        if (!tree[fullPath]) {
          tree[fullPath] = {
            name: part,
            path: fullPath,
            type: isFile ? 'file' : 'folder',
            children: []
          }
        }

        if (currentPath && tree[currentPath]) {
          if (!tree[currentPath].children) {
            tree[currentPath].children = []
          }
          if (!tree[currentPath].children!.find(c => c.path === fullPath)) {
            tree[currentPath].children!.push(tree[fullPath])
          }
        }

        currentPath = fullPath
      })
    })

    // Get root nodes
    return Object.values(tree).filter(node => {
      const parts = node.path.split('/')
      return parts.length === 1
    })
  }

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const renderNode = (node: FileNode, level: number = 0): React.ReactNode => {
    const isExpanded = expandedFolders.has(node.path)
    const isSelected = selectedFile === node.path

    if (node.type === 'folder') {
      return (
        <div key={node.path}>
          <div
            className={`flex items-center gap-1 px-2 py-1 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 rounded ${
              isSelected ? 'bg-blue-100 dark:bg-blue-900/30' : ''
            }`}
            style={{ paddingLeft: `${level * 16 + 8}px` }}
            onClick={() => toggleFolder(node.path)}
          >
            <span className="text-gray-500">{isExpanded ? '▼' : '▶'}</span>
            <span className="text-blue-500">{isExpanded ? '📂' : '📁'}</span>
            <span className="text-sm text-gray-700 dark:text-gray-300">{node.name}</span>
          </div>
          {isExpanded && node.children && (
            <div>
              {node.children.map(child => renderNode(child, level + 1))}
            </div>
          )}
        </div>
      )
    } else {
      return (
        <div
          key={node.path}
          className={`flex items-center gap-1 px-2 py-1 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 rounded ${
            isSelected ? 'bg-blue-100 dark:bg-blue-900/30' : ''
          }`}
          style={{ paddingLeft: `${level * 16 + 24}px` }}
          onClick={() => onFileSelect?.(node.path)}
        >
          <span className="text-gray-500">📄</span>
          <span className="text-sm text-gray-700 dark:text-gray-300">{node.name}</span>
        </div>
      )
    }
  }

  const tree = buildTree()

  if (files.length === 0) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 p-4">
        No files in project
      </div>
    )
  }

  return (
    <div className="overflow-y-auto max-h-96">
      {tree.map(node => renderNode(node))}
    </div>
  )
}
