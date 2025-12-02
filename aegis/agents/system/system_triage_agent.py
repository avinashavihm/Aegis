"""
System Triage Agent for routing tasks to specialized agents
"""

from aegis.registry import register_agent
from aegis.types import Agent, Result
from aegis.tools.inner import case_resolved, case_not_resolved
from .file_agent import get_file_agent
from .web_agent import get_web_agent
from .code_agent import get_code_agent


@register_agent(name="System Triage Agent", func_name="get_system_triage_agent")
def get_system_triage_agent(model: str) -> Agent:
    """
    System Triage Agent that routes tasks to specialized agents.
    
    Args:
        model: The model to use for the agent.
    """
    file_agent = get_file_agent(model)
    web_agent = get_web_agent(model)
    code_agent = get_code_agent(model)
    
    instructions = f"""You are a System Triage Agent that helps route user requests to the appropriate specialized agent.
Based on the user's request, determine which agent is best suited to handle it:

1. Use `transfer_to_file_agent` to transfer to {file_agent.name} - for file operations, reading/writing files, file management
2. Use `transfer_to_web_agent` to transfer to {web_agent.name} - for web browsing, fetching URLs, web searches
3. Use `transfer_to_code_agent` to transfer to {code_agent.name} - for code execution, programming tasks, running scripts

You should not stop trying to solve the user's request by transferring to another agent only until the task is completed.
When the task is fully completed, use case_resolved. If all agents have tried and the task cannot be completed, use case_not_resolved."""
    
    tools = [case_resolved, case_not_resolved]
    
    system_triage_agent = Agent(
        name="System Triage Agent",
        model=model,
        instructions=instructions,
        functions=tools,
        tool_choice="required",
        parallel_tool_calls=False
    )
    
    def transfer_to_file_agent(sub_task_description: str, context_variables: dict = None) -> Result:
        """Transfer to File Agent"""
        return Result(value=sub_task_description, agent=file_agent)
    
    def transfer_to_web_agent(sub_task_description: str, context_variables: dict = None) -> Result:
        """Transfer to Web Agent"""
        return Result(value=sub_task_description, agent=web_agent)
    
    def transfer_to_code_agent(sub_task_description: str, context_variables: dict = None) -> Result:
        """Transfer to Code Agent"""
        return Result(value=sub_task_description, agent=code_agent)
    
    def transfer_back_to_triage_agent(task_status: str, context_variables: dict = None) -> Result:
        """Transfer back to System Triage Agent"""
        return Result(value=task_status, agent=system_triage_agent)
    
    system_triage_agent.agent_teams = {
        file_agent.name: transfer_to_file_agent,
        web_agent.name: transfer_to_web_agent,
        code_agent.name: transfer_to_code_agent
    }
    
    system_triage_agent.functions.extend([
        transfer_to_file_agent,
        transfer_to_web_agent,
        transfer_to_code_agent
    ])
    
    # Add transfer back function to sub-agents
    file_agent.functions.append(transfer_back_to_triage_agent)
    web_agent.functions.append(transfer_back_to_triage_agent)
    code_agent.functions.append(transfer_back_to_triage_agent)
    
    return system_triage_agent

