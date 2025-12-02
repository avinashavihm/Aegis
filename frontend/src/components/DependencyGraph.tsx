import React, { useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  Position,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { Agent, Dependency } from '../types';

interface DependencyGraphProps {
  agents: Agent[];
  dependencies: Dependency[];
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({ agents, dependencies }) => {
  const { nodes, edges } = useMemo(() => {
    if (agents.length === 0) {
      return { nodes: [], edges: [] };
    }

    // Create nodes for each agent
    const agentNodes: Node[] = agents.map((agent, index) => {
      // Arrange nodes in a circle or grid layout
      const totalAgents = agents.length;
      const angle = (2 * Math.PI * index) / totalAgents;
      const radius = 200;
      const x = 400 + radius * Math.cos(angle);
      const y = 300 + radius * Math.sin(angle);

      // Color based on role
      const roleColors: Record<string, string> = {
        planner: '#3b82f6', // blue
        retriever: '#10b981', // green
        evaluator: '#f59e0b', // yellow
        executor: '#ef4444', // red
      };

      return {
        id: agent.id,
        type: 'default',
        position: { x, y },
        data: {
          label: (
            <div className="text-center">
              <div className="font-semibold text-sm">{agent.name}</div>
              <div className="text-xs text-gray-500 capitalize">{agent.role}</div>
            </div>
          ),
        },
        style: {
          background: roleColors[agent.role] || '#6b7280',
          color: '#fff',
          border: '2px solid #1f2937',
          borderRadius: '8px',
          padding: '10px',
          minWidth: '120px',
        },
      };
    });

    // Create edges for dependencies
    const dependencyEdges: Edge[] = dependencies.map((dep) => ({
      id: dep.id,
      source: dep.depends_on_agent_id,
      target: dep.agent_id,
      type: 'smoothstep',
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#6b7280',
      },
      style: {
        stroke: '#6b7280',
        strokeWidth: 2,
      },
      label: 'depends on',
      labelStyle: {
        fill: '#6b7280',
        fontWeight: 600,
        fontSize: '10px',
      },
    }));

    return { nodes: agentNodes, edges: dependencyEdges };
  }, [agents, dependencies]);

  if (agents.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <p className="text-gray-500">No agents to display</p>
      </div>
    );
  }

  return (
    <div className="w-full h-96 border border-gray-300 rounded-lg bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const agent = agents.find((a) => a.id === node.id);
            const roleColors: Record<string, string> = {
              planner: '#3b82f6',
              retriever: '#10b981',
              evaluator: '#f59e0b',
              executor: '#ef4444',
            };
            return roleColors[agent?.role || ''] || '#6b7280';
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>
    </div>
  );
};

