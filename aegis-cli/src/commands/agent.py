"""
Agent management commands - list, create, get, update, delete, run, status, export, import
"""

import typer
import json
import yaml
import os
from typing import Optional, List
from rich.console import Console
from src.api_client import get_api_client
from src.utils import OutputFormat, set_output_format, print_output, remove_ids_recursive, current_output_format
import httpx

app = typer.Typer()
console = Console()

# Default models for agent creation
DEFAULT_MODEL = "gemini/gemini-2.0-flash"

# Enhanced instructions template for agents that use tools and ask questions
ENHANCED_INSTRUCTIONS_TEMPLATE = """You are {name}, an intelligent AI assistant with access to various tools.

## Core Behaviors:
1. **Use Tools Actively**: You have tools available - ALWAYS use them when they can help. Don't just say you can't do something if a tool might help.
2. **Ask Clarifying Questions**: Before taking action, ask the user for any missing information you need. Don't make assumptions.
3. **Think Step-by-Step**: Break complex tasks into smaller steps and explain your reasoning.
4. **Be Proactive**: Suggest helpful next steps and related information.

## Tool Usage Guidelines:
- Review available tools before responding
- If a tool can help accomplish the task, USE IT
- Chain multiple tool calls when needed
- Report tool results clearly to the user

## Interaction Style:
- Be conversational and helpful
- Ask questions to understand requirements
- Confirm understanding before taking major actions
- Provide clear summaries of what you've done

{additional_instructions}
"""


def _handle_error(response: httpx.Response, action: str = "perform action"):
    """Handle API error responses consistently."""
    if response.status_code == 401:
        console.print("[red]Error:[/red] Not authenticated. Please login first.")
    elif response.status_code == 404:
        try:
            detail = response.json().get("detail", "Resource not found")
        except:
            detail = "Resource not found"
        console.print(f"[red]Error:[/red] {detail}")
    elif response.status_code == 400:
        try:
            detail = response.json().get("detail", response.text)
        except:
            detail = response.text
        console.print(f"[red]Error:[/red] {detail}")
    else:
        try:
            detail = response.json().get("detail", response.text)
        except:
            detail = response.text
        console.print(f"[red]Error {action}:[/red] {detail}")


@app.command(name="list")
def list_agents(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (active, inactive, draft)"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml, wide")
):
    """List all agents."""
    if output and output.lower() not in ["wide"]:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    wide_mode = output and output.lower() == "wide"
    client = get_api_client()
    
    try:
        response = client.list_agents(status=status, tag=tag)
        
        if response.status_code != 200:
            _handle_error(response, "listing agents")
            return
        
        agents = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_agents = []
            for a in agents:
                clean_agents.append(remove_ids_recursive({
                    "name": a["name"],
                    "description": a.get("description", ""),
                    "model": a.get("model", ""),
                    "status": a.get("status", ""),
                    "tools": a.get("tools", []),
                    "capabilities": a.get("capabilities", []),
                    "autonomous_mode": a.get("autonomous_mode", False),
                    "tags": a.get("tags", [])
                }))
            print_output(clean_agents, title="Agents")
        else:
            display_agents = []
            for a in agents:
                tools_str = ", ".join(a.get("tools", [])[:3])
                if len(a.get("tools", [])) > 3:
                    tools_str += f" (+{len(a['tools']) - 3})"
                
                tags_str = ", ".join(a.get("tags", [])[:2])
                
                item = {
                    "name": a["name"],
                    "model": a.get("model", "")[:20],
                    "status": a.get("status", ""),
                    "tools": tools_str or "-",
                }
                if wide_mode:
                    item["description"] = (a.get("description") or "")[:40]
                    item["tags"] = tags_str or "-"
                    item["autonomous"] = "Yes" if a.get("autonomous_mode") else "No"
                
                display_agents.append(item)
            
            columns = ["name", "model", "status", "tools"]
            if wide_mode:
                columns.extend(["description", "tags", "autonomous"])
            
            print_output(display_agents, columns=columns, title="Agents")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="get")
@app.command(name="show")
def show_agent(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Show agent details."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.get_agent(agent_identifier)
        
        if response.status_code != 200:
            _handle_error(response, "getting agent")
            return
        
        agent = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_agent = remove_ids_recursive({
                "name": agent["name"],
                "description": agent.get("description", ""),
                "model": agent.get("model", ""),
                "instructions": agent.get("instructions", ""),
                "tools": agent.get("tools", []),
                "custom_tool_ids": agent.get("custom_tool_ids", []),
                "mcp_server_ids": agent.get("mcp_server_ids", []),
                "file_ids": agent.get("file_ids", []),
                "tool_choice": agent.get("tool_choice", "auto"),
                "parallel_tool_calls": agent.get("parallel_tool_calls", True),
                "capabilities": agent.get("capabilities", []),
                "autonomous_mode": agent.get("autonomous_mode", False),
                "tags": agent.get("tags", []),
                "metadata": agent.get("metadata", {}),
                "status": agent.get("status", "")
            })
            print_output(clean_agent)
        else:
            # Header info
            console.print(f"\n[bold cyan]Agent:[/bold cyan] {agent['name']}")
            console.print(f"[bold]Model:[/bold] {agent.get('model', '-')}")
            console.print(f"[bold]Status:[/bold] {agent.get('status', '-')}")
            console.print(f"[bold]Autonomous:[/bold] {'Yes' if agent.get('autonomous_mode') else 'No'}")
            
            if agent.get("description"):
                console.print(f"[bold]Description:[/bold] {agent['description']}")
            
            if agent.get("instructions"):
                console.print(f"\n[bold]Instructions:[/bold]")
                console.print(agent["instructions"][:500])
                if len(agent.get("instructions", "")) > 500:
                    console.print("... (truncated)")
            
            tools = agent.get("tools", [])
            if tools:
                console.print(f"\n[bold]Tools ({len(tools)}):[/bold] {', '.join(tools[:10])}")
                if len(tools) > 10:
                    console.print(f"  ... and {len(tools) - 10} more")
            
            caps = agent.get("capabilities", [])
            if caps:
                cap_names = [c.get("name", "") if isinstance(c, dict) else str(c) for c in caps]
                console.print(f"[bold]Capabilities:[/bold] {', '.join(cap_names)}")
            
            tags = agent.get("tags", [])
            if tags:
                console.print(f"[bold]Tags:[/bold] {', '.join(tags)}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def create(
    name: str = typer.Argument(..., help="Agent name"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Model to use"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Agent description"),
    instructions: Optional[str] = typer.Option(None, "--instructions", "-i", help="System instructions"),
    instructions_file: Optional[str] = typer.Option(None, "--instructions-file", "-f", help="Load instructions from file"),
    tools: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated list of tools"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    autonomous: bool = typer.Option(True, "--autonomous/--no-autonomous", help="Enable autonomous mode"),
    status: str = typer.Option("active", "--status", "-s", help="Initial status (active, inactive, draft)"),
    enhanced: bool = typer.Option(True, "--enhanced/--basic", help="Use enhanced instructions template"),
    export_path: Optional[str] = typer.Option(None, "--export", "-e", help="Also export to YAML file"),
):
    """Create a new agent with enhanced tool-using instructions."""
    client = get_api_client()
    
    # Load instructions from file if provided
    actual_instructions = instructions
    if instructions_file:
        try:
            with open(instructions_file, "r") as f:
                actual_instructions = f.read()
        except Exception as e:
            console.print(f"[red]Error reading instructions file:[/red] {e}")
            return
    
    # Apply enhanced instructions template if not provided
    if not actual_instructions and enhanced:
        actual_instructions = ENHANCED_INSTRUCTIONS_TEMPLATE.format(
            name=name,
            additional_instructions=description or "Assist users with their tasks."
        )
    elif not actual_instructions:
        actual_instructions = "You are a helpful agent."
    
    payload = {
        "name": name,
        "model": model,
        "status": status,
        "autonomous_mode": autonomous,
        "instructions": actual_instructions
    }
    
    if description:
        payload["description"] = description
    if tools:
        payload["tools"] = [t.strip() for t in tools.split(",")]
    if tags:
        payload["tags"] = [t.strip() for t in tags.split(",")]
    
    try:
        response = client.create_agent(payload)
        
        if response.status_code == 201:
            agent = response.json()
            console.print(f"[green]Agent '{name}' created successfully![/green]")
            console.print(f"ID: {agent.get('id')}")
            
            # Export to YAML if requested
            if export_path:
                _export_agent_to_yaml(agent, export_path)
                console.print(f"[green]Exported to: {export_path}[/green]")
        else:
            _handle_error(response, "creating agent")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def update(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model to use"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    instructions: Optional[str] = typer.Option(None, "--instructions", "-i", help="System instructions"),
    instructions_file: Optional[str] = typer.Option(None, "--instructions-file", "-f", help="Load instructions from file"),
    tools: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated list of tools (replaces existing)"),
    add_tools: Optional[str] = typer.Option(None, "--add-tools", help="Comma-separated tools to add"),
    remove_tools: Optional[str] = typer.Option(None, "--remove-tools", help="Comma-separated tools to remove"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    autonomous: Optional[bool] = typer.Option(None, "--autonomous/--no-autonomous", help="Enable/disable autonomous mode"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Status (active, inactive, draft)")
):
    """Update an existing agent."""
    client = get_api_client()
    
    # Load instructions from file if provided
    actual_instructions = instructions
    if instructions_file:
        try:
            with open(instructions_file, "r") as f:
                actual_instructions = f.read()
        except Exception as e:
            console.print(f"[red]Error reading instructions file:[/red] {e}")
            return
    
    payload = {}
    
    if name:
        payload["name"] = name
    if model:
        payload["model"] = model
    if description:
        payload["description"] = description
    if actual_instructions:
        payload["instructions"] = actual_instructions
    if status:
        payload["status"] = status
    if autonomous is not None:
        payload["autonomous_mode"] = autonomous
    if tags:
        payload["tags"] = [t.strip() for t in tags.split(",")]
    
    # Handle tools updates
    if tools:
        payload["tools"] = [t.strip() for t in tools.split(",")]
    elif add_tools or remove_tools:
        # Need to get current tools first
        try:
            current = client.get_agent(agent_identifier)
            if current.status_code != 200:
                _handle_error(current, "getting agent")
                return
            current_tools = set(current.json().get("tools", []))
            
            if add_tools:
                current_tools.update(t.strip() for t in add_tools.split(","))
            if remove_tools:
                current_tools -= set(t.strip() for t in remove_tools.split(","))
            
            payload["tools"] = list(current_tools)
        except Exception as e:
            console.print(f"[red]Error getting current tools:[/red] {e}")
            return
    
    if not payload:
        console.print("[yellow]No updates specified.[/yellow]")
        return
    
    try:
        response = client.update_agent(agent_identifier, payload)
        
        if response.status_code == 200:
            console.print(f"[green]Agent '{agent_identifier}' updated successfully![/green]")
        else:
            _handle_error(response, "updating agent")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def delete(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Delete an agent."""
    client = get_api_client()
    
    if not yes and not typer.confirm(f"Are you sure you want to delete agent '{agent_identifier}'?"):
        return
    
    try:
        response = client.delete_agent(agent_identifier)
        
        if response.status_code == 204:
            console.print(f"[green]Agent '{agent_identifier}' deleted successfully.[/green]")
        else:
            _handle_error(response, "deleting agent")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def run(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    message: str = typer.Argument(..., help="Input message for the agent"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Context variables as JSON"),
    model_override: Optional[str] = typer.Option(None, "--model", "-m", help="Override agent's model"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Maximum conversation turns"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion and show result"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Execute an agent with the given input."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    # Parse context if provided
    context_vars = None
    if context:
        try:
            context_vars = json.loads(context)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing context JSON:[/red] {e}")
            return
    
    try:
        response = client.run_agent(
            agent_identifier, 
            message,
            context_variables=context_vars,
            model_override=model_override,
            max_turns=max_turns
        )
        
        if response.status_code == 201:
            run_data = response.json()
            run_id = run_data.get("id")
            console.print(f"[green]Agent run started![/green]")
            console.print(f"Run ID: {run_id}")
            console.print(f"Status: {run_data.get('status')}")
            
            if wait:
                console.print("\n[yellow]Waiting for completion...[/yellow]")
                import time
                while True:
                    time.sleep(2)
                    status_response = client.get_run(run_id)
                    if status_response.status_code == 200:
                        run_status = status_response.json()
                        if run_status.get("status") in ["completed", "failed", "cancelled"]:
                            console.print(f"\n[bold]Final Status:[/bold] {run_status.get('status')}")
                            if run_status.get("output"):
                                console.print(f"[bold]Output:[/bold]\n{run_status['output']}")
                            if run_status.get("error"):
                                console.print(f"[red]Error:[/red] {run_status['error']}")
                            break
                    else:
                        console.print("[red]Error checking status[/red]")
                        break
        else:
            _handle_error(response, "running agent")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def runs(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of runs to show"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """List runs for a specific agent."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.list_agent_runs(agent_identifier, status=status, limit=limit)
        
        if response.status_code != 200:
            _handle_error(response, "listing runs")
            return
        
        runs_data = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(runs_data, title="Agent Runs")
        else:
            display_runs = []
            for r in runs_data:
                display_runs.append({
                    "id": str(r.get("id", ""))[:8],
                    "status": r.get("status", ""),
                    "started_at": str(r.get("started_at") or "-")[:19],
                    "completed_at": str(r.get("completed_at") or "-")[:19]
                })
            
            print_output(display_runs, columns=["id", "status", "started_at", "completed_at"], 
                        title=f"Runs for Agent: {agent_identifier}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def status(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    new_status: Optional[str] = typer.Option(None, "--set", "-s", help="Set new status (active, inactive, draft)")
):
    """Get or set agent status."""
    client = get_api_client()
    
    try:
        if new_status:
            # Update status
            response = client.update_agent(agent_identifier, {"status": new_status})
            if response.status_code == 200:
                console.print(f"[green]Agent status updated to '{new_status}'[/green]")
            else:
                _handle_error(response, "updating status")
        else:
            # Get current status
            response = client.get_agent(agent_identifier)
            if response.status_code == 200:
                agent = response.json()
                console.print(f"Agent: {agent['name']}")
                console.print(f"Status: {agent.get('status', 'unknown')}")
            else:
                _handle_error(response, "getting agent")
                
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="clone")
def clone_agent(
    agent_identifier: str = typer.Argument(..., help="Agent to clone"),
    new_name: str = typer.Argument(..., help="Name for the cloned agent")
):
    """Clone an existing agent with a new name."""
    client = get_api_client()
    
    try:
        # Get source agent
        response = client.get_agent(agent_identifier)
        if response.status_code != 200:
            _handle_error(response, "getting source agent")
            return
        
        source = response.json()
        
        # Create new agent with same config
        payload = {
            "name": new_name,
            "description": f"Clone of {source['name']}. " + (source.get("description") or ""),
            "model": source.get("model"),
            "instructions": source.get("instructions"),
            "tools": source.get("tools", []),
            "custom_tool_ids": source.get("custom_tool_ids", []),
            "mcp_server_ids": source.get("mcp_server_ids", []),
            "tool_choice": source.get("tool_choice", "auto"),
            "parallel_tool_calls": source.get("parallel_tool_calls", True),
            "capabilities": source.get("capabilities", []),
            "autonomous_mode": source.get("autonomous_mode", False),
            "tags": source.get("tags", []),
            "metadata": source.get("metadata", {}),
            "status": "draft"  # Start cloned agent as draft
        }
        
        create_response = client.create_agent(payload)
        if create_response.status_code == 201:
            new_agent = create_response.json()
            console.print(f"[green]Agent cloned successfully![/green]")
            console.print(f"New agent: {new_name}")
            console.print(f"ID: {new_agent.get('id')}")
        else:
            _handle_error(create_response, "creating cloned agent")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def _export_agent_to_yaml(agent_data: dict, file_path: str):
    """Export agent data to a YAML file for deployment."""
    # Create deployment-ready YAML
    export_data = {
        "apiVersion": "aegis.io/v1",
        "kind": "Agent",
        "metadata": {
            "name": agent_data["name"],
            "labels": {
                "app": "aegis",
                "type": "agent"
            },
            "annotations": {
                "aegis.io/created-at": agent_data.get("created_at", ""),
                "aegis.io/updated-at": agent_data.get("updated_at", "")
            }
        },
        "spec": {
            "name": agent_data["name"],
            "description": agent_data.get("description", ""),
            "model": agent_data.get("model", DEFAULT_MODEL),
            "instructions": agent_data.get("instructions", ""),
            "tools": agent_data.get("tools", []),
            "custom_tool_ids": agent_data.get("custom_tool_ids", []),
            "mcp_server_ids": agent_data.get("mcp_server_ids", []),
            "file_ids": agent_data.get("file_ids", []),
            "tool_choice": agent_data.get("tool_choice", "auto"),
            "parallel_tool_calls": agent_data.get("parallel_tool_calls", True),
            "capabilities": agent_data.get("capabilities", []),
            "autonomous_mode": agent_data.get("autonomous_mode", True),
            "tags": agent_data.get("tags", []),
            "metadata": agent_data.get("metadata", {}),
            "status": agent_data.get("status", "active")
        }
    }
    
    # Ensure directory exists
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    with open(file_path, "w") as f:
        yaml.dump(export_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


@app.command(name="export")
def export_agent(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID to export"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output YAML file path"),
    include_all: bool = typer.Option(False, "--all", "-a", help="Export all agents to a directory")
):
    """Export agent(s) to YAML file(s) for deployment/backup."""
    client = get_api_client()
    
    try:
        if include_all:
            # Export all agents
            response = client.list_agents()
            if response.status_code != 200:
                _handle_error(response, "listing agents")
                return
            
            agents = response.json()
            output_dir = output_file or "agents"
            os.makedirs(output_dir, exist_ok=True)
            
            for agent in agents:
                file_path = os.path.join(output_dir, f"{agent['name']}.yaml")
                _export_agent_to_yaml(agent, file_path)
                console.print(f"[green]Exported:[/green] {agent['name']} -> {file_path}")
            
            console.print(f"\n[green]Exported {len(agents)} agents to {output_dir}/[/green]")
        else:
            # Export single agent
            response = client.get_agent(agent_identifier)
            if response.status_code != 200:
                _handle_error(response, "getting agent")
                return
            
            agent = response.json()
            file_path = output_file or f"{agent['name']}.yaml"
            _export_agent_to_yaml(agent, file_path)
            console.print(f"[green]Agent '{agent['name']}' exported to: {file_path}[/green]")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="import")
def import_agent(
    file_path: str = typer.Argument(..., help="YAML file to import"),
    update_existing: bool = typer.Option(False, "--update", "-u", help="Update if agent exists"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported without making changes")
):
    """Import agent from YAML file."""
    client = get_api_client()
    
    try:
        # Load YAML file
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        
        # Handle different YAML formats
        if "spec" in data:
            # Kubernetes-style manifest
            agent_data = data["spec"]
        elif "agent" in data:
            agent_data = data["agent"]
        else:
            # Direct agent format
            agent_data = data
        
        if dry_run:
            console.print("[yellow]Dry run - would import:[/yellow]")
            console.print(f"  Name: {agent_data.get('name')}")
            console.print(f"  Model: {agent_data.get('model')}")
            console.print(f"  Tools: {len(agent_data.get('tools', []))} tools")
            console.print(f"  Status: {agent_data.get('status', 'active')}")
            return
        
        # Prepare payload
        payload = {
            "name": agent_data["name"],
            "description": agent_data.get("description"),
            "model": agent_data.get("model", DEFAULT_MODEL),
            "instructions": agent_data.get("instructions", "You are a helpful agent."),
            "tools": agent_data.get("tools", []),
            "custom_tool_ids": agent_data.get("custom_tool_ids", []),
            "mcp_server_ids": agent_data.get("mcp_server_ids", []),
            "file_ids": agent_data.get("file_ids", []),
            "tool_choice": agent_data.get("tool_choice", "auto"),
            "parallel_tool_calls": agent_data.get("parallel_tool_calls", True),
            "capabilities": agent_data.get("capabilities", []),
            "autonomous_mode": agent_data.get("autonomous_mode", True),
            "tags": agent_data.get("tags", []),
            "metadata": agent_data.get("metadata", {}),
            "status": agent_data.get("status", "active")
        }
        
        # Check if agent exists
        existing_response = client.list_agents()
        existing_names = []
        if existing_response.status_code == 200:
            existing_names = [a["name"] for a in existing_response.json()]
        
        if payload["name"] in existing_names:
            if update_existing:
                # Find existing agent and update
                existing = next((a for a in existing_response.json() if a["name"] == payload["name"]), None)
                if existing:
                    response = client.update_agent(str(existing["id"]), payload)
                    if response.status_code == 200:
                        console.print(f"[green]Agent '{payload['name']}' updated from {file_path}[/green]")
                    else:
                        _handle_error(response, "updating agent")
            else:
                console.print(f"[yellow]Agent '{payload['name']}' already exists. Use --update to overwrite.[/yellow]")
        else:
            # Create new agent
            response = client.create_agent(payload)
            if response.status_code == 201:
                agent = response.json()
                console.print(f"[green]Agent '{payload['name']}' imported successfully![/green]")
                console.print(f"ID: {agent.get('id')}")
            else:
                _handle_error(response, "creating agent")
                
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {file_path}")
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML:[/red] {e}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="apply")
def apply_manifest(
    file_or_dir: str = typer.Argument(..., help="YAML file or directory to apply"),
    recursive: bool = typer.Option(False, "-r", "--recursive", help="Recursively apply from directory")
):
    """Apply agent manifest(s) from YAML - create or update (like kubectl apply)."""
    import glob
    
    files_to_apply = []
    
    if os.path.isdir(file_or_dir):
        pattern = os.path.join(file_or_dir, "**/*.yaml" if recursive else "*.yaml")
        files_to_apply = glob.glob(pattern, recursive=recursive)
        files_to_apply.extend(glob.glob(pattern.replace(".yaml", ".yml"), recursive=recursive))
    else:
        files_to_apply = [file_or_dir]
    
    if not files_to_apply:
        console.print(f"[yellow]No YAML files found in {file_or_dir}[/yellow]")
        return
    
    success_count = 0
    error_count = 0
    
    for file_path in files_to_apply:
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            
            kind = data.get("kind", "Agent")
            if kind != "Agent":
                console.print(f"[dim]Skipping {file_path} (kind: {kind})[/dim]")
                continue
            
            # Import with update
            console.print(f"Applying: {file_path}")
            import_agent(file_path, update_existing=True)
            success_count += 1
            
        except Exception as e:
            console.print(f"[red]Error applying {file_path}:[/red] {e}")
            error_count += 1
    
    console.print(f"\n[green]Applied: {success_count}[/green] | [red]Errors: {error_count}[/red]")


@app.command(name="enhance")
def enhance_instructions(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    additional: Optional[str] = typer.Option(None, "--additional", "-a", help="Additional instructions to include")
):
    """Enhance an agent's instructions with tool-usage and question-asking behaviors."""
    client = get_api_client()
    
    try:
        response = client.get_agent(agent_identifier)
        if response.status_code != 200:
            _handle_error(response, "getting agent")
            return
        
        agent = response.json()
        current_instructions = agent.get("instructions", "")
        
        # Build enhanced instructions
        enhanced = ENHANCED_INSTRUCTIONS_TEMPLATE.format(
            name=agent["name"],
            additional_instructions=additional or current_instructions
        )
        
        # Update the agent
        update_response = client.update_agent(str(agent["id"]), {"instructions": enhanced})
        if update_response.status_code == 200:
            console.print(f"[green]Agent '{agent['name']}' instructions enhanced![/green]")
            console.print("\n[bold]New instructions preview:[/bold]")
            console.print(enhanced[:500] + "..." if len(enhanced) > 500 else enhanced)
        else:
            _handle_error(update_response, "updating agent")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="debug")
def debug_agent(
    agent_identifier: str = typer.Argument(..., help="Agent name or ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full instructions")
):
    """Debug an agent - show tools, config, and potential issues."""
    client = get_api_client()
    
    try:
        response = client.get_agent(agent_identifier)
        if response.status_code != 200:
            _handle_error(response, "getting agent")
            return
        
        agent = response.json()
        
        console.print(f"\n[bold cyan]Agent Debug: {agent['name']}[/bold cyan]")
        console.print("=" * 50)
        
        # Basic info
        console.print(f"\n[bold]Basic Info:[/bold]")
        console.print(f"  ID: {agent['id']}")
        console.print(f"  Status: {agent['status']}")
        console.print(f"  Model: {agent.get('model', 'Not set')}")
        console.print(f"  Autonomous: {agent.get('autonomous_mode', False)}")
        console.print(f"  Tool Choice: {agent.get('tool_choice', 'auto')}")
        console.print(f"  Parallel Tools: {agent.get('parallel_tool_calls', True)}")
        
        # Tools analysis
        tools = agent.get("tools", [])
        custom_tool_ids = agent.get("custom_tool_ids", [])
        mcp_server_ids = agent.get("mcp_server_ids", [])
        
        console.print(f"\n[bold]Tools Configuration:[/bold]")
        if tools:
            console.print(f"  Built-in Tools ({len(tools)}):")
            for tool in tools:
                console.print(f"    - {tool}")
        else:
            console.print("  [yellow]⚠ No built-in tools configured[/yellow]")
        
        if custom_tool_ids:
            console.print(f"  Custom Tools ({len(custom_tool_ids)}): {custom_tool_ids}")
        
        if mcp_server_ids:
            console.print(f"  MCP Servers ({len(mcp_server_ids)}): {mcp_server_ids}")
        
        # Instructions analysis
        instructions = agent.get("instructions", "")
        console.print(f"\n[bold]Instructions Analysis:[/bold]")
        console.print(f"  Length: {len(instructions)} chars")
        
        issues = []
        
        # Check for common issues
        if not instructions or instructions == "You are a helpful agent.":
            issues.append("Generic/missing instructions - agent won't know how to use tools")
        
        if "tool" not in instructions.lower() and "function" not in instructions.lower():
            issues.append("No mention of tools in instructions - agent may not use them")
        
        if "question" not in instructions.lower() and "ask" not in instructions.lower():
            issues.append("No guidance on asking questions - agent may not gather info")
        
        if not tools and not custom_tool_ids:
            issues.append("No tools available - agent can't perform actions")
        
        if agent.get("tool_choice") == "none":
            issues.append("tool_choice is 'none' - agent will never use tools")
        
        if not agent.get("autonomous_mode"):
            issues.append("Autonomous mode is off - agent requires manual intervention")
        
        if issues:
            console.print(f"\n[bold red]Potential Issues ({len(issues)}):[/bold red]")
            for i, issue in enumerate(issues, 1):
                console.print(f"  {i}. {issue}")
            
            console.print("\n[bold]Recommendations:[/bold]")
            console.print("  • Run: aegis agent enhance <agent> --additional 'your specific instructions'")
            console.print("  • Add tools: aegis agent update <agent> --add-tools 'search_web,fetch_url'")
        else:
            console.print("  [green]✓ No obvious issues detected[/green]")
        
        if verbose:
            console.print(f"\n[bold]Full Instructions:[/bold]")
            console.print(instructions)
        else:
            console.print(f"\n[bold]Instructions Preview:[/bold]")
            preview = instructions[:300] + "..." if len(instructions) > 300 else instructions
            console.print(f"  {preview}")
            console.print("  [dim](use --verbose for full instructions)[/dim]")
        
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="template")
def create_template(
    template_type: str = typer.Argument("assistant", help="Template type: assistant, researcher, coder, travel, custom"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output file path"),
    name: str = typer.Option("my-agent", "--name", "-n", help="Agent name in template")
):
    """Generate an agent YAML template for common use cases."""
    
    templates = {
        "assistant": {
            "description": "General-purpose helpful assistant",
            "model": DEFAULT_MODEL,
            "instructions": ENHANCED_INSTRUCTIONS_TEMPLATE.format(
                name=name,
                additional_instructions="""
## Your Role
You are a general-purpose assistant that can help with various tasks.
- Answer questions accurately
- Help with research and analysis
- Provide clear explanations
- Use available tools when they can help
"""
            ),
            "tools": ["web_search", "fetch_url", "read_file", "write_file"],
            "tags": ["assistant", "general"]
        },
        "researcher": {
            "description": "Research assistant with web search capabilities",
            "model": DEFAULT_MODEL,
            "instructions": ENHANCED_INSTRUCTIONS_TEMPLATE.format(
                name=name,
                additional_instructions="""
## Your Role
You are a research specialist. Your job is to:
1. Understand the research question thoroughly
2. Use web search to find relevant information
3. Fetch and analyze web pages
4. Synthesize findings into clear reports
5. Always cite your sources

## Process
1. Ask clarifying questions about the research topic
2. Plan your search strategy
3. Execute searches and gather data
4. Analyze and summarize findings
5. Present conclusions with sources
"""
            ),
            "tools": ["web_search", "fetch_url", "extract_text", "summarize"],
            "tags": ["researcher", "web"]
        },
        "coder": {
            "description": "Code assistant that can write and execute code",
            "model": DEFAULT_MODEL,
            "instructions": ENHANCED_INSTRUCTIONS_TEMPLATE.format(
                name=name,
                additional_instructions="""
## Your Role
You are a coding assistant. You can:
1. Write code in various languages
2. Execute code safely
3. Debug and fix issues
4. Explain code clearly

## Guidelines
- Ask about requirements before writing code
- Write clean, well-documented code
- Test code when possible
- Explain your solutions
"""
            ),
            "tools": ["run_python", "run_shell", "read_file", "write_file"],
            "tags": ["coder", "developer"]
        },
        "travel": {
            "description": "Travel planning assistant",
            "model": DEFAULT_MODEL,
            "instructions": ENHANCED_INSTRUCTIONS_TEMPLATE.format(
                name=name,
                additional_instructions="""
## Your Role
You are a travel planning assistant. You help with:
1. Trip planning and itineraries
2. Finding flights, hotels, and activities
3. Providing destination information
4. Budget planning

## Key Questions to Ask
- Travel dates and flexibility
- Destination preferences
- Budget range
- Travel companions
- Preferred activities
- Special requirements (accessibility, dietary, etc.)

## Process
1. Gather all requirements through questions
2. Research options using available tools
3. Present multiple options with pros/cons
4. Help finalize and organize the plan
"""
            ),
            "tools": ["web_search", "fetch_url"],
            "tags": ["travel", "planning"]
        },
        "custom": {
            "description": "Custom agent template - modify as needed",
            "model": DEFAULT_MODEL,
            "instructions": "You are a helpful agent. Customize these instructions for your use case.",
            "tools": [],
            "tags": ["custom"]
        }
    }
    
    if template_type not in templates:
        console.print(f"[red]Unknown template:[/red] {template_type}")
        console.print(f"Available: {', '.join(templates.keys())}")
        return
    
    template = templates[template_type]
    
    manifest = {
        "apiVersion": "aegis.io/v1",
        "kind": "Agent",
        "metadata": {
            "name": name,
            "labels": {
                "app": "aegis",
                "type": "agent",
                "template": template_type
            }
        },
        "spec": {
            "name": name,
            "description": template["description"],
            "model": template["model"],
            "instructions": template["instructions"],
            "tools": template["tools"],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "autonomous_mode": True,
            "tags": template["tags"],
            "status": "draft"
        }
    }
    
    yaml_content = yaml.dump(manifest, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    if output_file:
        with open(output_file, "w") as f:
            f.write(yaml_content)
        console.print(f"[green]Template saved to: {output_file}[/green]")
    else:
        console.print(f"\n[bold cyan]Agent Template ({template_type}):[/bold cyan]\n")
        from rich.syntax import Syntax
        syntax = Syntax(yaml_content, "yaml", theme="monokai")
        console.print(syntax)
        console.print(f"\n[dim]Use --output to save to file[/dim]")
