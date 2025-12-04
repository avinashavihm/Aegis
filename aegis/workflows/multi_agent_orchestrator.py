"""
Multi-Agent Orchestrator for advanced agent collaboration

Provides dynamic routing, collaboration patterns, and orchestration
for multi-agent systems.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from aegis.types import Agent, Response, AgentCapability, TaskStatus
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


class CollaborationPattern(str, Enum):
    """Patterns for multi-agent collaboration"""
    SEQUENTIAL = "sequential"       # Agents work one after another
    PARALLEL = "parallel"           # Agents work simultaneously
    HIERARCHICAL = "hierarchical"   # Manager agent delegates to workers
    CONSENSUS = "consensus"         # Agents must agree on result
    VOTING = "voting"               # Majority decision from agents
    SPECIALIST = "specialist"       # Route to best-fit agent


class AgentStatus(str, Enum):
    """Status of an agent in the orchestration"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    name: str
    agent: Agent
    capabilities: List[AgentCapability] = field(default_factory=list)
    status: AgentStatus = AgentStatus.AVAILABLE
    current_task: Optional[str] = None
    task_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0
    last_active: Optional[str] = None


@dataclass
class TaskAssignment:
    """Assignment of a task to an agent"""
    task_id: str
    agent_name: str
    task_description: str
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    assigned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


class MultiAgentOrchestrator:
    """
    Orchestrates multiple agents for complex task execution.
    Supports various collaboration patterns and dynamic routing.
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.tasks: Dict[str, TaskAssignment] = {}
        self.routing_rules: List[Dict[str, Any]] = []
        self.default_pattern = CollaborationPattern.SPECIALIST
        self.task_history: List[Dict[str, Any]] = []
        self._task_counter = 0
    
    def register_agent(self, agent: Agent, capabilities: List[AgentCapability] = None):
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: The agent to register
            capabilities: Agent's capabilities for routing
        """
        self.agents[agent.name] = AgentInfo(
            name=agent.name,
            agent=agent,
            capabilities=capabilities or agent.capabilities
        )
        logger.info(f"Registered agent: {agent.name}", title="Orchestrator")
    
    def unregister_agent(self, agent_name: str) -> bool:
        """Unregister an agent"""
        if agent_name in self.agents:
            del self.agents[agent_name]
            return True
        return False
    
    def add_routing_rule(self, keywords: List[str], agent_name: str, priority: int = 0):
        """
        Add a routing rule for task assignment.
        
        Args:
            keywords: Keywords that trigger this rule
            agent_name: Agent to route to
            priority: Rule priority (higher = checked first)
        """
        self.routing_rules.append({
            "keywords": keywords,
            "agent_name": agent_name,
            "priority": priority
        })
        self.routing_rules.sort(key=lambda r: r["priority"], reverse=True)
    
    def find_best_agent(self, task_description: str) -> Optional[str]:
        """
        Find the best agent for a task based on routing rules and capabilities.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Name of the best agent or None
        """
        task_lower = task_description.lower()
        
        # Check routing rules first
        for rule in self.routing_rules:
            if any(kw in task_lower for kw in rule["keywords"]):
                agent_name = rule["agent_name"]
                if agent_name in self.agents:
                    agent_info = self.agents[agent_name]
                    if agent_info.status == AgentStatus.AVAILABLE:
                        return agent_name
        
        # Check agent capabilities
        best_agent = None
        best_score = 0
        
        for name, info in self.agents.items():
            if info.status != AgentStatus.AVAILABLE:
                continue
            
            score = 0
            for cap in info.capabilities:
                for keyword in cap.keywords:
                    if keyword.lower() in task_lower:
                        score += cap.priority + 1
            
            # Factor in success rate
            if info.task_count > 0:
                success_rate = info.success_count / info.task_count
                score *= (0.5 + success_rate * 0.5)
            
            if score > best_score:
                best_score = score
                best_agent = name
        
        return best_agent
    
    def assign_task(self, task_description: str, agent_name: str = None,
                    priority: int = 0) -> TaskAssignment:
        """
        Assign a task to an agent.
        
        Args:
            task_description: Description of the task
            agent_name: Specific agent (or auto-select)
            priority: Task priority
            
        Returns:
            TaskAssignment
        """
        self._task_counter += 1
        task_id = f"task-{self._task_counter}"
        
        # Auto-select agent if not specified
        if not agent_name:
            agent_name = self.find_best_agent(task_description)
        
        if not agent_name:
            # Create assignment in pending state
            assignment = TaskAssignment(
                task_id=task_id,
                agent_name="unassigned",
                task_description=task_description,
                priority=priority,
                status=TaskStatus.PENDING
            )
        else:
            assignment = TaskAssignment(
                task_id=task_id,
                agent_name=agent_name,
                task_description=task_description,
                priority=priority
            )
            
            # Update agent status
            if agent_name in self.agents:
                self.agents[agent_name].current_task = task_id
        
        self.tasks[task_id] = assignment
        return assignment
    
    def execute_sequential(self, tasks: List[str], 
                           executor: Callable[[Agent, str], Response]) -> Dict[str, Any]:
        """
        Execute tasks sequentially through agents.
        
        Args:
            tasks: List of task descriptions
            executor: Function to execute tasks
            
        Returns:
            Results from all tasks
        """
        results = {
            "pattern": CollaborationPattern.SEQUENTIAL.value,
            "tasks": [],
            "success": True
        }
        
        context = {}
        
        for i, task_desc in enumerate(tasks):
            assignment = self.assign_task(task_desc)
            
            if assignment.agent_name == "unassigned":
                results["tasks"].append({
                    "task_id": assignment.task_id,
                    "status": "failed",
                    "error": "No suitable agent found"
                })
                results["success"] = False
                continue
            
            agent_info = self.agents[assignment.agent_name]
            
            try:
                # Execute task
                assignment.status = TaskStatus.IN_PROGRESS
                assignment.started_at = datetime.now().isoformat()
                
                start_time = datetime.now()
                response = executor(agent_info.agent, task_desc)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Update assignment
                assignment.status = TaskStatus.COMPLETED
                assignment.completed_at = datetime.now().isoformat()
                assignment.result = str(response.messages[-1] if response.messages else "")
                
                # Update agent stats
                agent_info.task_count += 1
                agent_info.success_count += 1
                agent_info.avg_response_time = (
                    (agent_info.avg_response_time * (agent_info.task_count - 1) + duration) 
                    / agent_info.task_count
                )
                agent_info.last_active = datetime.now().isoformat()
                agent_info.status = AgentStatus.AVAILABLE
                agent_info.current_task = None
                
                # Update context for next task
                context["previous_result"] = assignment.result
                
                results["tasks"].append({
                    "task_id": assignment.task_id,
                    "agent": assignment.agent_name,
                    "status": "completed",
                    "duration": duration
                })
                
            except Exception as e:
                assignment.status = TaskStatus.FAILED
                assignment.error = str(e)
                agent_info.task_count += 1
                agent_info.status = AgentStatus.AVAILABLE
                agent_info.current_task = None
                
                results["tasks"].append({
                    "task_id": assignment.task_id,
                    "agent": assignment.agent_name,
                    "status": "failed",
                    "error": str(e)
                })
                results["success"] = False
        
        return results
    
    async def execute_parallel(self, tasks: List[str],
                               executor: Callable[[Agent, str], Response]) -> Dict[str, Any]:
        """
        Execute tasks in parallel across agents.
        
        Args:
            tasks: List of task descriptions
            executor: Function to execute tasks
            
        Returns:
            Results from all tasks
        """
        results = {
            "pattern": CollaborationPattern.PARALLEL.value,
            "tasks": [],
            "success": True
        }
        
        async def execute_single(task_desc: str) -> Dict[str, Any]:
            assignment = self.assign_task(task_desc)
            
            if assignment.agent_name == "unassigned":
                return {
                    "task_id": assignment.task_id,
                    "status": "failed",
                    "error": "No suitable agent found"
                }
            
            agent_info = self.agents[assignment.agent_name]
            
            try:
                assignment.status = TaskStatus.IN_PROGRESS
                assignment.started_at = datetime.now().isoformat()
                
                start_time = datetime.now()
                
                # Run in thread pool for sync executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, executor, agent_info.agent, task_desc
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                assignment.status = TaskStatus.COMPLETED
                assignment.completed_at = datetime.now().isoformat()
                assignment.result = str(response.messages[-1] if response.messages else "")
                
                agent_info.task_count += 1
                agent_info.success_count += 1
                agent_info.status = AgentStatus.AVAILABLE
                
                return {
                    "task_id": assignment.task_id,
                    "agent": assignment.agent_name,
                    "status": "completed",
                    "duration": duration
                }
                
            except Exception as e:
                assignment.status = TaskStatus.FAILED
                assignment.error = str(e)
                agent_info.task_count += 1
                agent_info.status = AgentStatus.AVAILABLE
                
                return {
                    "task_id": assignment.task_id,
                    "agent": assignment.agent_name,
                    "status": "failed",
                    "error": str(e)
                }
        
        # Execute all tasks in parallel
        task_results = await asyncio.gather(*[execute_single(t) for t in tasks])
        
        results["tasks"] = list(task_results)
        results["success"] = all(r["status"] == "completed" for r in task_results)
        
        return results
    
    def execute_hierarchical(self, task: str, manager_agent: str,
                             worker_agents: List[str],
                             executor: Callable[[Agent, str], Response]) -> Dict[str, Any]:
        """
        Execute a task hierarchically with a manager delegating to workers.
        
        Args:
            task: Main task description
            manager_agent: Name of the manager agent
            worker_agents: Names of worker agents
            executor: Function to execute tasks
            
        Returns:
            Results
        """
        results = {
            "pattern": CollaborationPattern.HIERARCHICAL.value,
            "manager": manager_agent,
            "workers": [],
            "success": True
        }
        
        if manager_agent not in self.agents:
            return {"success": False, "error": f"Manager agent {manager_agent} not found"}
        
        manager_info = self.agents[manager_agent]
        
        # Manager analyzes task and creates subtasks
        plan_prompt = f"""Analyze this task and break it into subtasks for {len(worker_agents)} workers:
Task: {task}

Workers available: {', '.join(worker_agents)}

Provide a plan with subtasks."""
        
        try:
            plan_response = executor(manager_info.agent, plan_prompt)
            results["plan"] = str(plan_response.messages[-1] if plan_response.messages else "")
        except Exception as e:
            return {"success": False, "error": f"Manager planning failed: {e}"}
        
        # Execute subtasks with workers
        for worker_name in worker_agents:
            if worker_name not in self.agents:
                results["workers"].append({
                    "agent": worker_name,
                    "status": "failed",
                    "error": "Agent not found"
                })
                continue
            
            worker_info = self.agents[worker_name]
            
            try:
                worker_response = executor(worker_info.agent, task)
                results["workers"].append({
                    "agent": worker_name,
                    "status": "completed",
                    "result": str(worker_response.messages[-1] if worker_response.messages else "")
                })
            except Exception as e:
                results["workers"].append({
                    "agent": worker_name,
                    "status": "failed",
                    "error": str(e)
                })
                results["success"] = False
        
        # Manager synthesizes results
        synthesis_prompt = f"""Synthesize the results from workers:
{json.dumps(results['workers'], indent=2)}

Provide a final summary."""
        
        try:
            synthesis_response = executor(manager_info.agent, synthesis_prompt)
            results["final_result"] = str(synthesis_response.messages[-1] if synthesis_response.messages else "")
        except Exception as e:
            results["synthesis_error"] = str(e)
        
        return results
    
    def get_agent_status(self, agent_name: str = None) -> Dict[str, Any]:
        """Get status of agents"""
        if agent_name:
            if agent_name not in self.agents:
                return {"error": f"Agent {agent_name} not found"}
            info = self.agents[agent_name]
            return {
                "name": info.name,
                "status": info.status.value,
                "current_task": info.current_task,
                "task_count": info.task_count,
                "success_count": info.success_count,
                "success_rate": info.success_count / info.task_count if info.task_count > 0 else 0,
                "avg_response_time": info.avg_response_time,
                "capabilities": [c.name for c in info.capabilities],
                "last_active": info.last_active
            }
        
        return {
            "agents": [
                {
                    "name": info.name,
                    "status": info.status.value,
                    "task_count": info.task_count,
                    "success_rate": info.success_count / info.task_count if info.task_count > 0 else 0
                }
                for info in self.agents.values()
            ],
            "total_agents": len(self.agents),
            "available_agents": sum(1 for a in self.agents.values() if a.status == AgentStatus.AVAILABLE)
        }
    
    def get_task_status(self, task_id: str = None) -> Dict[str, Any]:
        """Get status of tasks"""
        if task_id:
            if task_id not in self.tasks:
                return {"error": f"Task {task_id} not found"}
            task = self.tasks[task_id]
            return {
                "task_id": task.task_id,
                "agent": task.agent_name,
                "description": task.task_description,
                "status": task.status.value,
                "assigned_at": task.assigned_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "result": task.result,
                "error": task.error
            }
        
        return {
            "tasks": [
                {
                    "task_id": t.task_id,
                    "agent": t.agent_name,
                    "status": t.status.value
                }
                for t in self.tasks.values()
            ],
            "total_tasks": len(self.tasks),
            "completed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "pending": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestration statistics"""
        total_tasks = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        
        return {
            "total_agents": len(self.agents),
            "available_agents": sum(1 for a in self.agents.values() if a.status == AgentStatus.AVAILABLE),
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "success_rate": completed / total_tasks if total_tasks > 0 else 0,
            "routing_rules": len(self.routing_rules),
            "patterns_available": [p.value for p in CollaborationPattern]
        }


# We need to import json for the hierarchical method
import json

# Global orchestrator instance
multi_agent_orchestrator = MultiAgentOrchestrator()

