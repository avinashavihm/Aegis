"""
Orchestrator Agent for managing multi-agent collaboration
"""

from aegis.registry import register_agent
from aegis.types import Agent, Result, AgentCapability
from aegis.tools.inner import case_resolved, case_not_resolved


@register_agent(name="Orchestrator Agent", func_name="get_orchestrator_agent")
def get_orchestrator_agent(model: str) -> Agent:
    """
    Orchestrator Agent that manages multi-agent collaboration.
    
    Args:
        model: The model to use for the agent.
    """
    
    instructions = """You are the Orchestrator Agent, responsible for coordinating multiple agents to complete complex tasks.

CORE RESPONSIBILITIES:
1. Analyze complex tasks and decompose them into subtasks
2. Assign subtasks to the most appropriate agents
3. Monitor task progress and handle failures
4. Synthesize results from multiple agents
5. Ensure task completion and quality

AVAILABLE AGENTS:
- File Agent: File operations, reading/writing files
- Web Agent: Web browsing, fetching URLs, web searches
- Code Agent: Code execution, programming tasks

ORCHESTRATION STRATEGIES:
1. SEQUENTIAL: Tasks that depend on each other
   - Use when output of one task is input to the next
   - Example: Read file -> Process data -> Write result

2. PARALLEL: Independent tasks
   - Use when tasks don't depend on each other
   - Example: Fetch multiple URLs simultaneously

3. HIERARCHICAL: Complex tasks with subtask delegation
   - Break down into smaller tasks
   - Assign to specialized agents
   - Synthesize results

WORKFLOW:
1. Receive task from user
2. Analyze task complexity and requirements
3. Identify which agents are needed
4. Create execution plan
5. Transfer to appropriate agents in sequence
6. Monitor for errors and handle gracefully
7. Compile final results

TRANSFER FUNCTIONS:
- transfer_to_file_agent: For file operations
- transfer_to_web_agent: For web operations
- transfer_to_code_agent: For code execution

RULES:
- Always complete the full task before marking as resolved
- If an agent fails, try alternative approaches
- Provide clear status updates during complex operations
- Use case_resolved only when the entire task is complete

When all subtasks are complete, use case_resolved with a comprehensive summary."""
    
    # Create transfer functions
    from aegis.agents.system.file_agent import get_file_agent
    from aegis.agents.system.web_agent import get_web_agent
    from aegis.agents.system.code_agent import get_code_agent
    
    file_agent = get_file_agent(model)
    web_agent = get_web_agent(model)
    code_agent = get_code_agent(model)
    
    def transfer_to_file_agent(sub_task_description: str, context_variables: dict = None) -> Result:
        """
        Transfer a file-related subtask to the File Agent.
        
        Args:
            sub_task_description: Description of the file operation to perform
        """
        return Result(value=f"Transferring to File Agent: {sub_task_description}", agent=file_agent)
    
    def transfer_to_web_agent(sub_task_description: str, context_variables: dict = None) -> Result:
        """
        Transfer a web-related subtask to the Web Agent.
        
        Args:
            sub_task_description: Description of the web operation to perform
        """
        return Result(value=f"Transferring to Web Agent: {sub_task_description}", agent=web_agent)
    
    def transfer_to_code_agent(sub_task_description: str, context_variables: dict = None) -> Result:
        """
        Transfer a code-related subtask to the Code Agent.
        
        Args:
            sub_task_description: Description of the code operation to perform
        """
        return Result(value=f"Transferring to Code Agent: {sub_task_description}", agent=code_agent)
    
    tools = [
        transfer_to_file_agent,
        transfer_to_web_agent,
        transfer_to_code_agent,
        case_resolved,
        case_not_resolved
    ]
    
    capabilities = [
        AgentCapability(
            name="orchestration",
            description="Coordinates multiple agents for complex tasks",
            keywords=["orchestrate", "coordinate", "manage", "complex", "multi-step"],
            priority=10
        ),
        AgentCapability(
            name="task_decomposition",
            description="Breaks down complex tasks into subtasks",
            keywords=["decompose", "break down", "subtasks", "plan"],
            priority=8
        )
    ]
    
    return Agent(
        name="Orchestrator Agent",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required",
        parallel_tool_calls=False,
        capabilities=capabilities
    )

