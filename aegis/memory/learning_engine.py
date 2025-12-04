"""
Learning Engine for adaptive agent behavior

Provides learning capabilities for agents to improve over time
based on past executions and outcomes.
"""

import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict

from aegis.memory.agent_memory import AgentMemory, AgentMemoryManager, ExecutionRecord
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


@dataclass
class LearningInsight:
    """An insight derived from learning"""
    insight_id: str
    insight_type: str  # strategy, warning, optimization, pattern
    description: str
    confidence: float
    applicable_to: List[str]  # task types this applies to
    recommendations: List[str]
    evidence: List[str]  # execution IDs that support this
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FailureAnalysis:
    """Analysis of execution failures"""
    failure_type: str
    count: int
    common_causes: List[str]
    recovery_strategies: List[str]
    last_occurred: str


class LearningEngine:
    """
    Engine for learning from agent executions and providing adaptive recommendations.
    """
    
    def __init__(self, memory_manager: AgentMemoryManager = None):
        """
        Initialize the learning engine.
        
        Args:
            memory_manager: Optional custom memory manager
        """
        self.memory_manager = memory_manager or AgentMemoryManager
        self.insights: Dict[str, LearningInsight] = {}
        self.failure_analyses: Dict[str, FailureAnalysis] = {}
        self.learning_callbacks: List[Callable] = []
    
    def register_learning_callback(self, callback: Callable):
        """Register a callback for when new insights are discovered"""
        self.learning_callbacks.append(callback)
    
    def _trigger_callbacks(self, insight: LearningInsight):
        """Trigger registered callbacks"""
        for callback in self.learning_callbacks:
            try:
                callback(insight)
            except Exception as e:
                logger.warning(f"Learning callback error: {e}", title="LearningEngine")
    
    def learn_from_execution(self, agent_name: str, execution: ExecutionRecord) -> List[LearningInsight]:
        """
        Learn from a single execution.
        
        Args:
            agent_name: Name of the agent
            execution: The execution record
            
        Returns:
            List of new insights discovered
        """
        new_insights = []
        memory = self.memory_manager.get_memory(agent_name)
        
        if execution.success:
            # Learn from successful execution
            insights = self._analyze_success(memory, execution)
            new_insights.extend(insights)
        else:
            # Learn from failure
            insights = self._analyze_failure(memory, execution)
            new_insights.extend(insights)
        
        # Look for patterns across executions
        pattern_insights = self._discover_patterns(memory)
        new_insights.extend(pattern_insights)
        
        # Store and trigger callbacks for new insights
        for insight in new_insights:
            self.insights[insight.insight_id] = insight
            self._trigger_callbacks(insight)
        
        return new_insights
    
    def _analyze_success(self, memory: AgentMemory, execution: ExecutionRecord) -> List[LearningInsight]:
        """Analyze successful execution for learnings"""
        insights = []
        
        # Check if this is a new successful strategy
        similar = memory.get_similar_executions(execution.task, limit=10)
        successful_similar = [e for e in similar if e.success and e.execution_id != execution.execution_id]
        
        if successful_similar:
            # Compare tool sequences
            this_tools = set(execution.tools_used)
            for other in successful_similar:
                other_tools = set(other.tools_used)
                
                if this_tools != other_tools and len(this_tools) < len(other_tools):
                    # Found a more efficient approach
                    insight = LearningInsight(
                        insight_id=f"efficiency-{execution.execution_id}",
                        insight_type="optimization",
                        description=f"Found more efficient tool usage for {memory._extract_task_type(execution.task)} tasks",
                        confidence=0.7,
                        applicable_to=[memory._extract_task_type(execution.task)],
                        recommendations=[f"Consider using {this_tools} instead of {other_tools}"],
                        evidence=[execution.execution_id, other.execution_id]
                    )
                    insights.append(insight)
        
        return insights
    
    def _analyze_failure(self, memory: AgentMemory, execution: ExecutionRecord) -> List[LearningInsight]:
        """Analyze failed execution for learnings"""
        insights = []
        
        # Categorize the failure
        error_type = self._categorize_error(execution.error or "Unknown error")
        
        # Update failure analysis
        if error_type in self.failure_analyses:
            analysis = self.failure_analyses[error_type]
            analysis.count += 1
            analysis.last_occurred = datetime.now().isoformat()
        else:
            self.failure_analyses[error_type] = FailureAnalysis(
                failure_type=error_type,
                count=1,
                common_causes=[execution.error or "Unknown"],
                recovery_strategies=self._get_recovery_strategies(error_type),
                last_occurred=datetime.now().isoformat()
            )
        
        # Check for repeated failures
        similar_failures = [
            e for e in memory.executions
            if not e.success and 
            memory._extract_task_type(e.task) == memory._extract_task_type(execution.task)
        ]
        
        if len(similar_failures) >= 3:
            insight = LearningInsight(
                insight_id=f"warning-{memory._extract_task_type(execution.task)}-{len(similar_failures)}",
                insight_type="warning",
                description=f"Repeated failures detected for {memory._extract_task_type(execution.task)} tasks",
                confidence=0.8,
                applicable_to=[memory._extract_task_type(execution.task)],
                recommendations=self._get_recovery_strategies(error_type),
                evidence=[e.execution_id for e in similar_failures[-3:]]
            )
            insights.append(insight)
        
        return insights
    
    def _categorize_error(self, error: str) -> str:
        """Categorize an error message"""
        error_lower = error.lower()
        
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "permission" in error_lower or "access denied" in error_lower:
            return "permission"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found"
        elif "connection" in error_lower or "network" in error_lower:
            return "network"
        elif "rate limit" in error_lower or "too many" in error_lower:
            return "rate_limit"
        elif "invalid" in error_lower or "parse" in error_lower:
            return "validation"
        else:
            return "unknown"
    
    def _get_recovery_strategies(self, error_type: str) -> List[str]:
        """Get recovery strategies for an error type"""
        strategies = {
            "timeout": [
                "Increase timeout duration",
                "Break task into smaller chunks",
                "Check network connectivity"
            ],
            "permission": [
                "Verify credentials are correct",
                "Check file/resource permissions",
                "Ensure API keys have required scopes"
            ],
            "not_found": [
                "Verify the resource path/URL",
                "Check if resource exists before accessing",
                "Use fallback resources"
            ],
            "network": [
                "Retry with exponential backoff",
                "Check network connectivity",
                "Use cached data if available"
            ],
            "rate_limit": [
                "Implement rate limiting",
                "Add delays between requests",
                "Use batch operations where possible"
            ],
            "validation": [
                "Validate input data before processing",
                "Check data format and types",
                "Handle edge cases"
            ],
            "unknown": [
                "Log detailed error information",
                "Review execution context",
                "Try alternative approaches"
            ]
        }
        return strategies.get(error_type, strategies["unknown"])
    
    def _discover_patterns(self, memory: AgentMemory) -> List[LearningInsight]:
        """Discover patterns from execution history"""
        insights = []
        
        if len(memory.executions) < 5:
            return insights  # Not enough data
        
        # Find tool sequences that consistently succeed
        tool_sequence_results: Dict[str, Dict[str, int]] = {}
        
        for execution in memory.executions[-50:]:  # Last 50 executions
            sequence_key = ",".join(sorted(execution.tools_used))
            if sequence_key not in tool_sequence_results:
                tool_sequence_results[sequence_key] = {"success": 0, "failure": 0}
            
            if execution.success:
                tool_sequence_results[sequence_key]["success"] += 1
            else:
                tool_sequence_results[sequence_key]["failure"] += 1
        
        # Identify reliable patterns
        for sequence, results in tool_sequence_results.items():
            total = results["success"] + results["failure"]
            if total >= 3:
                success_rate = results["success"] / total
                
                if success_rate >= 0.9:
                    insight = LearningInsight(
                        insight_id=f"pattern-{hash(sequence) % 10000}",
                        insight_type="pattern",
                        description=f"Highly reliable tool sequence identified: {sequence}",
                        confidence=success_rate,
                        applicable_to=["general"],
                        recommendations=[f"Prefer using tool sequence: {sequence}"],
                        evidence=[]
                    )
                    
                    if insight.insight_id not in self.insights:
                        insights.append(insight)
        
        return insights
    
    def get_recommendations(self, agent_name: str, task: str) -> Dict[str, Any]:
        """
        Get recommendations for a task based on learning.
        
        Args:
            agent_name: Name of the agent
            task: The task description
            
        Returns:
            Dictionary with recommendations
        """
        memory = self.memory_manager.get_memory(agent_name)
        
        # Get strategy from memory
        strategy = memory.get_recommended_strategy(task)
        
        # Get relevant insights
        task_type = memory._extract_task_type(task)
        relevant_insights = [
            i for i in self.insights.values()
            if task_type in i.applicable_to or "general" in i.applicable_to
        ]
        
        # Get failure warnings
        warnings = [
            asdict(self.failure_analyses[ft])
            for ft in self.failure_analyses
            if self.failure_analyses[ft].count >= 2
        ]
        
        return {
            "task": task,
            "task_type": task_type,
            "recommended_strategy": strategy,
            "insights": [asdict(i) for i in relevant_insights],
            "warnings": warnings,
            "similar_successful_executions": len([
                e for e in memory.get_similar_executions(task, limit=10) if e.success
            ])
        }
    
    def get_agent_performance(self, agent_name: str) -> Dict[str, Any]:
        """
        Get performance metrics for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Performance metrics
        """
        memory = self.memory_manager.get_memory(agent_name)
        stats = memory.get_statistics()
        
        # Calculate trends
        recent_executions = memory.executions[-20:] if memory.executions else []
        recent_success_rate = sum(1 for e in recent_executions if e.success) / len(recent_executions) if recent_executions else 0
        
        # Get improvement areas
        improvement_areas = []
        for ft, analysis in self.failure_analyses.items():
            if analysis.count >= 3:
                improvement_areas.append({
                    "area": ft,
                    "failure_count": analysis.count,
                    "strategies": analysis.recovery_strategies
                })
        
        return {
            "agent_name": agent_name,
            "overall_stats": stats,
            "recent_success_rate": recent_success_rate,
            "trend": "improving" if recent_success_rate > stats.get("success_rate", 0) else "stable",
            "patterns_learned": len(memory.patterns),
            "insights_generated": len([i for i in self.insights.values() if agent_name in str(i.evidence)]),
            "improvement_areas": improvement_areas
        }
    
    def get_insights(self, insight_type: str = None, min_confidence: float = 0.0) -> List[LearningInsight]:
        """
        Get learning insights.
        
        Args:
            insight_type: Optional filter by type
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of insights
        """
        insights = list(self.insights.values())
        
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
        
        insights = [i for i in insights if i.confidence >= min_confidence]
        
        return sorted(insights, key=lambda i: i.confidence, reverse=True)
    
    def export_learnings(self) -> Dict[str, Any]:
        """Export all learnings for persistence"""
        return {
            "insights": {k: asdict(v) for k, v in self.insights.items()},
            "failure_analyses": {k: asdict(v) for k, v in self.failure_analyses.items()},
            "exported_at": datetime.now().isoformat()
        }
    
    def import_learnings(self, data: Dict[str, Any]):
        """Import learnings from exported data"""
        for k, v in data.get("insights", {}).items():
            self.insights[k] = LearningInsight(**v)
        
        for k, v in data.get("failure_analyses", {}).items():
            self.failure_analyses[k] = FailureAnalysis(**v)


# Global learning engine instance
learning_engine = LearningEngine()

