"""
Main CLI interface for Aegis
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
# Optional prompt_toolkit imports (for future enhancement)
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import HTML
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from aegis.cli.utils import print_logo, single_select_menu, print_success, print_error, print_info
from aegis import Aegis
from aegis.types import Agent
from aegis.config import COMPLETION_MODEL
from aegis.logger import LoggerManager, AegisLogger
from aegis.environment.local_env import LocalEnv
from aegis.environment.file_env import FileEnv
from aegis.environment.web_env import WebEnv
from aegis.agents.system.system_triage_agent import get_system_triage_agent
from aegis.agents.meta.agent_editor import get_agent_editor_agent
from aegis.agents.meta.tool_editor import get_tool_editor_agent
from aegis.agents.meta.workflow_editor import get_workflow_editor_agent

console = Console()


def clear_screen():
    """Clear the screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def user_mode(model: str, context_variables: dict):
    """User mode - multi-agent research assistant"""
    logger = LoggerManager.get_logger()
    console.print("\n[bold green]User Mode - Multi-Agent Research Assistant[/bold green]")
    console.print("[dim]Type 'exit' to quit[/dim]\n")
    
    system_triage_agent = get_system_triage_agent(model)
    assert system_triage_agent.agent_teams != {}, "System Triage Agent must have agent teams"
    
    messages = []
    agent = system_triage_agent
    agents = {system_triage_agent.name.replace(' ', '_'): system_triage_agent}
    
    for agent_name in system_triage_agent.agent_teams.keys():
        agents[agent_name.replace(' ', '_')] = system_triage_agent.agent_teams[agent_name]("placeholder", context_variables).agent
    
    client = Aegis(log_path=logger)
    
    while True:
        try:
            query = input("\nYou: ").strip()
            if query.lower() == 'exit':
                console.print("\n[bold green]User mode completed. See you next time! 👋[/bold green]")
                break
            
            if not query:
                continue
            
            # Check for agent mentions
            words = query.split()
            for word in words:
                if word.startswith('@') and word[1:] in agents.keys():
                    agent = agents[word.replace('@', '')]
                    console.print(f"[dim]Switching to {agent.name}[/dim]")
            
            if hasattr(agent, "name"):
                agent_name = agent.name
                console.print(f"[bold magenta]@{agent_name}[/bold magenta] is working on your request...")
                
                messages.append({"role": "user", "content": query})
                response = client.run(agent, messages, context_variables, debug=False)
                messages.extend(response.messages)
                
                # Extract final response - similar logic to agent_editor_mode
                import re
                model_answer = None
                
                if response.messages:
                    # First, check for case_resolved or case_not_resolved tool results
                    for msg in reversed(response.messages):
                        if msg.get("role") == "tool":
                            tool_name = msg.get("name", "")
                            content = msg.get("content", "")
                            
                            if tool_name == "case_resolved" and content:
                                solution_match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL)
                                if solution_match:
                                    model_answer = solution_match.group(1).strip()
                                else:
                                    result_match = re.search(r'result of the case resolution is: (.*?)(?:\.|$)', content, re.DOTALL)
                                    if result_match:
                                        result = result_match.group(1).strip()
                                        solution_match = re.search(r'<solution>(.*?)</solution>', result, re.DOTALL)
                                        if solution_match:
                                            model_answer = solution_match.group(1).strip()
                                        else:
                                            model_answer = result
                                    else:
                                        model_answer = content
                                break
                            
                            if tool_name == "case_not_resolved" and content:
                                reason_match = re.search(r'reason is: (.*?)(?:\. But|$)', content, re.DOTALL)
                                if reason_match:
                                    model_answer = f"Task not completed: {reason_match.group(1).strip()}"
                                else:
                                    model_answer = content
                                break
                    
                    # Second, look for the last assistant message with content
                    if not model_answer:
                        last_message = response.messages[-1]
                        model_answer_raw = last_message.get('content', '') if isinstance(last_message, dict) else getattr(last_message, 'content', '')
                        
                        if model_answer_raw:
                            # attempt to parse model_answer
                            if model_answer_raw.startswith('Case resolved'):
                                solution_match = re.findall(r'<solution>(.*?)</solution>', model_answer_raw, re.DOTALL)
                                if len(solution_match) > 0:
                                    model_answer = solution_match[0]
                                else:
                                    model_answer = model_answer_raw
                            else: 
                                model_answer = model_answer_raw
                    
                    # Default if nothing found
                    if not model_answer:
                        model_answer = "No response content received. Check the tool results above for details."
                else:
                    model_answer = "No response received"
                
                console.print(f"\n[bold green]@{agent_name}:[/bold green] {model_answer}\n")
                agent = response.agent
            else:
                console.print(f"[red]Unknown agent: {agent}[/red]")
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]Interrupted. Exiting user mode...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            logger.error(f"Error in user mode: {str(e)}", title="User Mode Error")


def agent_editor_mode(model: str, context_variables: dict):
    """Agent Editor mode - create agents through conversation"""
    logger = LoggerManager.get_logger()
    console.print("\n[bold green]Agent Editor Mode[/bold green]")
    console.print("[dim]Create agents through natural language. Type 'exit' to quit[/dim]\n")
    
    agent_editor = get_agent_editor_agent(model)
    messages = []
    client = Aegis(log_path=logger)
    
    while True:
        try:
            query = input("\nYou: ").strip()
            if query.lower() == 'exit':
                console.print("\n[bold green]Agent Editor mode completed. See you next time! 👋[/bold green]")
                break
            
            if not query:
                continue
            
            console.print(f"[bold magenta]Agent Editor[/bold magenta] is working on your request...")
            messages.append({"role": "user", "content": query})
            response = client.run(agent_editor, messages, context_variables, debug=False)
            messages.extend(response.messages)
            
            # Extract final response - prioritize tool results, especially from run_agent
            import re
            model_answer = None
            
            if response.messages:
                # First, check for run_agent tool results (these contain the actual agent output)
                for msg in reversed(response.messages):
                    if msg.get("role") == "tool" and msg.get("name") == "run_agent":
                        content = msg.get("content", "")
                        if content and not content.startswith("[ERROR]"):
                            # If it starts with [SUCCESS], extract the actual content after the header
                            if content.startswith("[SUCCESS]"):
                                # Extract content after [SUCCESS] Agent 'name' completed.\n\n
                                success_match = re.search(r'\[SUCCESS\].*?completed\.\n\n(.*)', content, re.DOTALL)
                                if success_match:
                                    content = success_match.group(1).strip()
                            
                            # Extract solution from <solution> tags if present
                            solution_match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL)
                            if solution_match:
                                model_answer = solution_match.group(1).strip()
                            else:
                                # Check if it's a case_resolved/case_not_resolved message
                                if "Case resolved" in content or "Case not resolved" in content or "Task not completed" in content:
                                    # Extract the actual result/reason
                                    result_match = re.search(r'result of the case resolution is: (.*?)(?:\.|$)', content, re.DOTALL)
                                    if result_match:
                                        result = result_match.group(1).strip()
                                        solution_match = re.search(r'<solution>(.*?)</solution>', result, re.DOTALL)
                                        if solution_match:
                                            model_answer = solution_match.group(1).strip()
                                        else:
                                            model_answer = result
                                    else:
                                        # Extract failure reason for case_not_resolved
                                        reason_match = re.search(r'Reason: (.*?)(?:\n\n|$)', content, re.DOTALL)
                                        if reason_match:
                                            reason = reason_match.group(1).strip()
                                            # Check for note
                                            note_match = re.search(r'Note: (.*?)(?:\n|$)', content, re.DOTALL)
                                            if note_match:
                                                note = note_match.group(1).strip()
                                                model_answer = f"Task not completed.\n\nReason: {reason}\n\nNote: {note}"
                                            else:
                                                model_answer = f"Task not completed.\n\nReason: {reason}"
                                        else:
                                            model_answer = content
                                else:
                                    model_answer = content
                            break
                
                # Second, check for case_resolved or case_not_resolved tool results
                if not model_answer:
                    for msg in reversed(response.messages):
                        if msg.get("role") == "tool":
                            tool_name = msg.get("name", "")
                            content = msg.get("content", "")
                            
                            if tool_name == "case_resolved" and content:
                                solution_match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL)
                                if solution_match:
                                    model_answer = solution_match.group(1).strip()
                                else:
                                    result_match = re.search(r'result of the case resolution is: (.*?)(?:\.|$)', content, re.DOTALL)
                                    if result_match:
                                        model_answer = result_match.group(1).strip()
                                    else:
                                        model_answer = content
                                break
                            
                            if tool_name == "case_not_resolved" and content:
                                reason_match = re.search(r'reason is: (.*?)(?:\. But|$)', content, re.DOTALL)
                                if reason_match:
                                    model_answer = f"Task not completed: {reason_match.group(1).strip()}"
                                else:
                                    model_answer = content
                                break
                
                # Third, look for the last assistant message with content
                if not model_answer:
                    for msg in reversed(response.messages):
                        if msg.get("role") == "assistant":
                            content = msg.get("content")
                            if content and content.strip() and content.strip() != "None":
                                # Try to extract solution from <solution> tags
                                solution_match = re.search(r'<solution>(.*?)</solution>', content, re.DOTALL)
                                if solution_match:
                                    model_answer = solution_match.group(1).strip()
                                else:
                                    model_answer = content
                                break
                
                # Last resort: check if there are any tool results with useful info
                if not model_answer:
                    for msg in reversed(response.messages):
                        if msg.get("role") == "tool":
                            content = msg.get("content", "")
                            if content and len(content) > 20 and "PLACEHOLDER" not in content:
                                model_answer = content[:500]  # Return first 500 chars
                                break
                
                # Default message if nothing found
                if not model_answer:
                    # Check if agent made tool calls
                    tool_calls_made = []
                    for msg in response.messages:
                        if msg.get("role") == "assistant" and msg.get("tool_calls"):
                            for tc in msg.get("tool_calls", []):
                                tool_name = tc.get("function", {}).get("name", "unknown")
                                tool_calls_made.append(tool_name)
                    
                    if tool_calls_made:
                        model_answer = f"Agent executed tools: {', '.join(set(tool_calls_made))}. Check the tool results above for details."
                    else:
                        model_answer = "No response content received. The agent may have executed tools. Check the logs for details."
            else:
                model_answer = "No response received"
            
            console.print(f"\n[bold green]Agent Editor:[/bold green] {model_answer}\n")
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]Interrupted. Exiting agent editor mode...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            logger.error(f"Error in agent editor mode: {str(e)}", title="Agent Editor Error")


def workflow_editor_mode(model: str, context_variables: dict):
    """Workflow Editor mode - create workflows through conversation"""
    logger = LoggerManager.get_logger()
    console.print("\n[bold green]Workflow Editor Mode[/bold green]")
    console.print("[dim]Create workflows through natural language. Type 'exit' to quit[/dim]\n")
    
    workflow_editor = get_workflow_editor_agent(model)
    messages = []
    client = Aegis(log_path=logger)
    
    while True:
        try:
            query = input("\nYou: ").strip()
            if query.lower() == 'exit':
                console.print("\n[bold green]Workflow Editor mode completed. See you next time! 👋[/bold green]")
                break
            
            if not query:
                continue
            
            console.print(f"[bold magenta]Workflow Editor[/bold magenta] is working on your request...")
            messages.append({"role": "user", "content": query})
            response = client.run(workflow_editor, messages, context_variables, debug=False)
            messages.extend(response.messages)
            
            # Handle None content gracefully
            if response.messages:
                last_message = response.messages[-1]
                model_answer = last_message.get('content') if isinstance(last_message, dict) else getattr(last_message, 'content', None)
                if model_answer is None:
                    model_answer = "No response content received. The agent may have executed tools. Check the logs for details."
            else:
                model_answer = "No response received"
            
            console.print(f"\n[bold green]Workflow Editor:[/bold green] {model_answer}\n")
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]Interrupted. Exiting workflow editor mode...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            logger.error(f"Error in workflow editor mode: {str(e)}", title="Workflow Editor Error")


def main():
    """Main entry point for Aegis CLI"""
    print_logo()
    
    # Setup logger
    log_path = os.path.join("logs", "aegis.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    LoggerManager.set_logger(AegisLogger(log_path=log_path))
    
    # Setup environments
    code_env = LocalEnv(workspace_name="aegis_workspace")
    file_env = FileEnv(workspace_name="aegis_workspace")
    web_env = WebEnv()
    
    context_variables = {
        "working_dir": "aegis_workspace",
        "code_env": code_env,
        "web_env": web_env,
        "file_env": file_env
    }
    
    model = COMPLETION_MODEL
    console.print(f"[dim]Using model: {model}[/dim]\n")
    
    # Main menu loop
    while True:
        try:
            mode = single_select_menu(
                ['User Mode', 'Agent Editor', 'Workflow Editor', 'Exit'],
                "Please select a mode:"
            )
            
            clear_screen()
            print_logo()
            
            if mode == 'User Mode':
                user_mode(model, context_variables)
            elif mode == 'Agent Editor':
                agent_editor_mode(model, context_variables)
            elif mode == 'Workflow Editor':
                workflow_editor_mode(model, context_variables)
            elif mode == 'Exit':
                console.print("\n[bold green]Thank you for using Aegis! 👋[/bold green]\n")
                break
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]Interrupted. Exiting...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            logger = LoggerManager.get_logger()
            logger.error(f"Error in main: {str(e)}", title="Main Error")

