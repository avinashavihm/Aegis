"""
Agent-specific memory for tracking agent behavior and learning
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class ExecutionRecord:
    """Record of an agent execution"""
    execution_id: str
    agent_name: str
    task: str
    tools_used: List[str]
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    patterns: List[str] = field(default_factory=list)


@dataclass
class AgentPattern:
    """A learned pattern from agent executions"""
    pattern_id: str
    agent_name: str
    task_type: str
    successful_strategy: str
    tool_sequence: List[str]
    success_rate: float
    usage_count: int
    last_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentMemory:
    """
    Memory system for individual agents.
    Tracks executions, learns patterns, and provides recommendations.
    """
    
    def __init__(self, agent_name: str, storage_path: Optional[str] = None):
        """
        Initialize agent memory.
        
        Args:
            agent_name: Name of the agent
            storage_path: Path to persist memory
        """
        self.agent_name = agent_name
        self.storage_path = storage_path
        self.executions: List[ExecutionRecord] = []
        self.patterns: Dict[str, AgentPattern] = {}
        self.knowledge_base: Dict[str, Any] = {}
        
        if storage_path:
            self._load_memory()
    
    def record_execution(self, task: str, tools_used: List[str], success: bool,
                        result: str = None, error: str = None, 
                        duration: float = 0.0, context: Dict = None) -> ExecutionRecord:
        """
        Record an agent execution.
        
        Args:
            task: The task that was executed
            tools_used: List of tools used
            success: Whether execution was successful
            result: Execution result
            error: Error message if failed
            duration: Duration in seconds
            context: Additional context
            
        Returns:
            ExecutionRecord
        """
        execution = ExecutionRecord(
            execution_id=f"{self.agent_name}-{len(self.executions)+1}",
            agent_name=self.agent_name,
            task=task,
            tools_used=tools_used,
            success=success,
            result=result,
            error=error,
            duration_seconds=duration,
            context=context or {}
        )
        
        self.executions.append(execution)
        
        # Update patterns based on this execution
        if success:
            self._update_patterns(execution)
        
        if self.storage_path:
            self._save_memory()
        
        return execution
    
    def _update_patterns(self, execution: ExecutionRecord):
        """Update patterns based on successful execution"""
        # Create a pattern identifier based on task type and tools
        task_type = self._extract_task_type(execution.task)
        tool_sequence = ",".join(execution.tools_used)
        pattern_id = f"{task_type}-{hash(tool_sequence) % 10000}"
        
        if pattern_id in self.patterns:
            # Update existing pattern
            pattern = self.patterns[pattern_id]
            pattern.usage_count += 1
            pattern.success_rate = (pattern.success_rate * (pattern.usage_count - 1) + 1.0) / pattern.usage_count
            pattern.last_used = datetime.now().isoformat()
        else:
            # Create new pattern
            self.patterns[pattern_id] = AgentPattern(
                pattern_id=pattern_id,
                agent_name=self.agent_name,
                task_type=task_type,
                successful_strategy=f"Used tools: {tool_sequence}",
                tool_sequence=execution.tools_used,
                success_rate=1.0,
                usage_count=1,
                last_used=datetime.now().isoformat()
            )
    
    def _extract_task_type(self, task: str) -> str:
        """Extract a task type category from task description"""
        task_lower = task.lower()
        
        # Simple keyword-based categorization
        if any(kw in task_lower for kw in ["read", "file", "load"]):
            return "file_operation"
        elif any(kw in task_lower for kw in ["write", "save", "create"]):
            return "file_creation"
        elif any(kw in task_lower for kw in ["search", "find", "query"]):
            return "search"
        elif any(kw in task_lower for kw in ["web", "fetch", "http", "url"]):
            return "web_operation"
        elif any(kw in task_lower for kw in ["code", "execute", "run", "script"]):
            return "code_execution"
        elif any(kw in task_lower for kw in ["analyze", "summarize", "extract"]):
            return "analysis"
        else:
            return "general"
    
    def get_recommended_strategy(self, task: str) -> Optional[Dict[str, Any]]:
        """
        Get a recommended strategy for a task based on learned patterns.
        
        Args:
            task: The task description
            
        Returns:
            Dictionary with recommended strategy or None
        """
        task_type = self._extract_task_type(task)
        
        # Find matching patterns
        matching_patterns = [
            p for p in self.patterns.values()
            if p.task_type == task_type and p.success_rate >= 0.7
        ]
        
        if not matching_patterns:
            return None
        
        # Sort by success rate and usage count
        best_pattern = max(matching_patterns, 
                          key=lambda p: (p.success_rate, p.usage_count))
        
        return {
            "pattern_id": best_pattern.pattern_id,
            "task_type": task_type,
            "recommended_tools": best_pattern.tool_sequence,
            "strategy": best_pattern.successful_strategy,
            "confidence": best_pattern.success_rate,
            "based_on_executions": best_pattern.usage_count
        }
    
    def get_similar_executions(self, task: str, limit: int = 5) -> List[ExecutionRecord]:
        """
        Get similar past executions.
        
        Args:
            task: The task to find similar executions for
            limit: Maximum number of results
            
        Returns:
            List of similar ExecutionRecords
        """
        task_type = self._extract_task_type(task)
        task_lower = task.lower()
        
        scored_executions = []
        for execution in self.executions:
            score = 0
            
            # Same task type
            if self._extract_task_type(execution.task) == task_type:
                score += 5
            
            # Keyword overlap
            exec_words = set(execution.task.lower().split())
            task_words = set(task_lower.split())
            overlap = len(exec_words & task_words)
            score += overlap
            
            # Successful executions get a boost
            if execution.success:
                score += 3
            
            scored_executions.append((score, execution))
        
        # Sort by score and return top results
        scored_executions.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored_executions[:limit]]
    
    def store_knowledge(self, key: str, value: Any, category: str = "general"):
        """
        Store a piece of knowledge.
        
        Args:
            key: Knowledge key
            value: Knowledge value
            category: Knowledge category
        """
        if category not in self.knowledge_base:
            self.knowledge_base[category] = {}
        
        self.knowledge_base[category][key] = {
            "value": value,
            "stored_at": datetime.now().isoformat()
        }
        
        if self.storage_path:
            self._save_memory()
    
    def retrieve_knowledge(self, key: str, category: str = "general") -> Optional[Any]:
        """
        Retrieve stored knowledge.
        
        Args:
            key: Knowledge key
            category: Knowledge category
            
        Returns:
            Stored value or None
        """
        if category in self.knowledge_base and key in self.knowledge_base[category]:
            return self.knowledge_base[category][key]["value"]
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if not self.executions:
            return {
                "agent_name": self.agent_name,
                "total_executions": 0,
                "success_rate": 0,
                "patterns_learned": 0
            }
        
        successful = sum(1 for e in self.executions if e.success)
        
        return {
            "agent_name": self.agent_name,
            "total_executions": len(self.executions),
            "successful_executions": successful,
            "failed_executions": len(self.executions) - successful,
            "success_rate": successful / len(self.executions),
            "patterns_learned": len(self.patterns),
            "knowledge_entries": sum(len(v) for v in self.knowledge_base.values()),
            "most_used_tools": self._get_most_used_tools(),
            "task_type_distribution": self._get_task_distribution()
        }
    
    def _get_most_used_tools(self, limit: int = 5) -> List[tuple]:
        """Get most frequently used tools"""
        tool_counts: Dict[str, int] = {}
        for execution in self.executions:
            for tool in execution.tools_used:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tools[:limit]
    
    def _get_task_distribution(self) -> Dict[str, int]:
        """Get distribution of task types"""
        distribution: Dict[str, int] = {}
        for execution in self.executions:
            task_type = self._extract_task_type(execution.task)
            distribution[task_type] = distribution.get(task_type, 0) + 1
        return distribution
    
    def _save_memory(self):
        """Save memory to storage"""
        if not self.storage_path:
            return
        
        os.makedirs(self.storage_path, exist_ok=True)
        memory_file = os.path.join(self.storage_path, f"{self.agent_name}_memory.json")
        
        data = {
            "agent_name": self.agent_name,
            "executions": [asdict(e) for e in self.executions[-1000:]],  # Keep last 1000
            "patterns": {k: asdict(v) for k, v in self.patterns.items()},
            "knowledge_base": self.knowledge_base
        }
        
        with open(memory_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_memory(self):
        """Load memory from storage"""
        if not self.storage_path:
            return
        
        memory_file = os.path.join(self.storage_path, f"{self.agent_name}_memory.json")
        
        if not os.path.exists(memory_file):
            return
        
        try:
            with open(memory_file, 'r') as f:
                data = json.load(f)
            
            self.executions = [ExecutionRecord(**e) for e in data.get("executions", [])]
            self.patterns = {k: AgentPattern(**v) for k, v in data.get("patterns", {}).items()}
            self.knowledge_base = data.get("knowledge_base", {})
        except Exception:
            # If loading fails, start fresh
            pass
    
    def clear(self):
        """Clear all memory"""
        self.executions = []
        self.patterns = {}
        self.knowledge_base = {}
        
        if self.storage_path:
            memory_file = os.path.join(self.storage_path, f"{self.agent_name}_memory.json")
            if os.path.exists(memory_file):
                os.remove(memory_file)


class AgentMemoryManager:
    """
    Manages memory for multiple agents.
    """
    
    _memories: Dict[str, AgentMemory] = {}
    _storage_path: Optional[str] = None
    
    @classmethod
    def set_storage_path(cls, path: str):
        """Set the storage path for all agent memories"""
        cls._storage_path = path
        os.makedirs(path, exist_ok=True)
    
    @classmethod
    def get_memory(cls, agent_name: str) -> AgentMemory:
        """
        Get or create memory for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            AgentMemory instance
        """
        if agent_name not in cls._memories:
            cls._memories[agent_name] = AgentMemory(agent_name, cls._storage_path)
        return cls._memories[agent_name]
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """List all agents with memory"""
        return list(cls._memories.keys())
    
    @classmethod
    def get_global_statistics(cls) -> Dict[str, Any]:
        """Get statistics across all agents"""
        all_stats = {
            "total_agents": len(cls._memories),
            "agent_stats": {}
        }
        
        total_executions = 0
        total_successful = 0
        
        for agent_name, memory in cls._memories.items():
            stats = memory.get_statistics()
            all_stats["agent_stats"][agent_name] = stats
            total_executions += stats.get("total_executions", 0)
            total_successful += stats.get("successful_executions", 0)
        
        all_stats["total_executions"] = total_executions
        all_stats["overall_success_rate"] = total_successful / total_executions if total_executions > 0 else 0
        
        return all_stats

