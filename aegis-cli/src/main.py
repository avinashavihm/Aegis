import typer
from typing import Optional
from src.commands.user import login
from src.utils import OutputFormat, set_output_format

# Import command modules for subcommands
from src.commands import agent as agent_commands
from src.commands import workflow as workflow_commands
from src.commands import run as run_commands
from src.commands import tool as tool_commands

__version__ = "0.2.0"

app = typer.Typer(
    name="aegis",
    help="Aegis CLI - Agentic Ops Platform\n\nManage agents, workflows, tools, and runs with precision.",
    add_completion=False,
    no_args_is_help=True
)


def version_callback(value: bool):
    if value:
        typer.echo(f"Aegis CLI version {__version__}")
        raise typer.Exit()

# Add command groups
app.add_typer(agent_commands.app, name="agent", help="Manage agents (list, create, run, etc.)")
app.add_typer(workflow_commands.app, name="workflow", help="Manage workflows (list, create, run, etc.)")
app.add_typer(run_commands.app, name="run", help="Manage runs (list, get, cancel, stats)")
app.add_typer(tool_commands.app, name="tool", help="Manage tools (list, show, custom tools)")

# Add plural aliases for convenience
app.add_typer(agent_commands.app, name="agents", hidden=True)
app.add_typer(workflow_commands.app, name="workflows", hidden=True)
app.add_typer(run_commands.app, name="runs", hidden=True)
app.add_typer(tool_commands.app, name="tools", hidden=True)

@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json, yaml, wide. Default: text"
    )
):
    """
    Aegis CLI - Agentic Ops Platform
    
    Manage agents, workflows, tools, runs, and access control.
    
    Commands:
      agent     - Manage AI agents
      workflow  - Manage multi-step workflows  
      run       - View and manage execution runs
      tool      - Browse and manage tools
      
    Quick shortcuts:
      run-agent    - Execute an agent
      run-workflow - Execute a workflow
      stats        - Show run statistics
      watch        - Watch a run in real-time
      logs         - View run logs
    """
    if output is None:
        from src.config import get_default_output_format
        output_format = OutputFormat(get_default_output_format())
        set_output_format(output_format)
    elif output.lower() != "wide":
        # Only set format if not wide (wide is handled per-command)
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            pass  # Will be handled by individual commands

app.command()(login)

# Import and add change-password as top-level command
from src.commands.user import change_password
app.command(name="change-password")(change_password)


def normalize_resource_type(resource_type: str) -> str:
    """Normalize resource type aliases to standard names."""
    resource_type = resource_type.lower()
    alias_map = {
        # Workspaces
        "ws": "workspace",
        "wss": "workspaces",
        "workspace": "workspace",
        "workspaces": "workspaces",
        # Users
        "user": "user",
        "users": "users",
        # Teams
        "team": "team",
        "teams": "teams",
        # Roles
        "role": "role",
        "roles": "roles",
        # Policies
        "policy": "policy",
        "policies": "policies",
        # Agents
        "agent": "agent",
        "agents": "agents",
        # Workflows
        "workflow": "workflow",
        "workflows": "workflows",
        "wf": "workflow",
        "wfs": "workflows",
        # Runs
        "run": "run",
        "runs": "runs",
        # Tools
        "tool": "tool",
        "tools": "tools",
    }
    return alias_map.get(resource_type, resource_type)


@app.command()
def create(
    resource_type: str = typer.Argument(..., help="Resource type (user, team, role, policy, workspace/ws, agent, workflow)"),
    name: str = typer.Argument(..., help="Resource name/identifier"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    email: Optional[str] = typer.Option(None, "--email", help="Email (for user)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password (for user)"),
    full_name: Optional[str] = typer.Option(None, "--name", help="Full name (for user)"),
    policy: Optional[str] = typer.Option(None, "--policy", help="Policy ID/name (for role)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="File path (for policy/workflow steps)"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Content JSON string (for policy)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model (for agent)"),
    instructions: Optional[str] = typer.Option(None, "--instructions", "-i", help="Instructions (for agent)"),
    tools: Optional[str] = typer.Option(None, "--tools", "-t", help="Comma-separated tools (for agent)"),
    mode: Optional[str] = typer.Option(None, "--mode", help="Execution mode (for workflow)"),
    status: Optional[str] = typer.Option("active", "--status", "-s", help="Status (active, inactive, draft)")
):
    """Create a new resource."""
    resource_type = normalize_resource_type(resource_type)
    
    if resource_type == "user":
        from src.commands.user import create as create_user
        if not email or not password:
            typer.echo("[red]Error:[/red] --email and --password are required for user creation")
            raise typer.Exit(1)
        create_user(name, email=email, password=password, full_name=full_name)
    elif resource_type == "team":
        from src.commands.team import create as create_team
        create_team(name, description=description)
    elif resource_type == "role":
        from src.commands.role import create as create_role
        policy_ids = [policy] if policy else None
        create_role(name, description=description, policy_ids=policy_ids)
    elif resource_type == "policy":
        from src.commands.policy import create as create_policy
        create_policy(name, content=content, file=file, description=description)
    elif resource_type == "workspace":
        from src.commands.workspace import create as create_workspace
        create_workspace(name, description=description)
    elif resource_type == "agent":
        from src.commands.agent import create as create_agent
        create_agent(
            name=name,
            model=model or "gpt-4o",
            description=description,
            instructions=instructions,
            tools=tools,
            status=status
        )
    elif resource_type == "workflow":
        from src.commands.workflow import create as create_workflow
        create_workflow(
            name=name,
            description=description,
            execution_mode=mode or "sequential",
            steps_file=file,
            status=status
        )
    else:
        typer.echo(f"[red]Error:[/red] Unknown resource type: {resource_type}")
        typer.echo("Valid types: user, team, role, policy, workspace/ws, agent, workflow")
        raise typer.Exit(1)


@app.command()
def delete(
    resource_type: str = typer.Argument(..., help="Resource type (user, team, role, policy, workspace/ws, agent, workflow, run)"),
    identifier: str = typer.Argument(..., help="Resource identifier (name or ID)"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Delete a resource."""
    resource_type = normalize_resource_type(resource_type)
    
    if resource_type == "user":
        from src.commands.user import delete as delete_user
        delete_user(identifier, yes=yes)
    elif resource_type == "team":
        from src.commands.team import delete as delete_team
        delete_team(identifier, yes=yes)
    elif resource_type == "role":
        from src.commands.role import delete as delete_role
        delete_role(identifier, yes=yes)
    elif resource_type == "policy":
        from src.commands.policy import delete as delete_policy
        delete_policy(identifier, yes=yes)
    elif resource_type == "workspace":
        from src.commands.workspace import delete as delete_workspace
        delete_workspace(identifier, yes=yes)
    elif resource_type == "agent":
        from src.commands.agent import delete as delete_agent
        delete_agent(identifier, yes=yes)
    elif resource_type == "workflow":
        from src.commands.workflow import delete as delete_workflow
        delete_workflow(identifier, yes=yes)
    elif resource_type == "run":
        from src.commands.run import delete as delete_run
        delete_run(identifier, yes=yes)
    else:
        typer.echo(f"[red]Error:[/red] Unknown resource type: {resource_type}")
        typer.echo("Valid types: user, team, role, policy, workspace/ws, agent, workflow, run")
        raise typer.Exit(1)


@app.command()
def attach_user_role(
    user: str = typer.Option(..., "--user", "-u", help="Username or user ID"),
    role: str = typer.Option(..., "--role", "-r", help="Role name or ID")
):
    """Attach a role to a user."""
    from rich.console import Console
    from src.api_client import get_api_client
    import httpx
    
    console = Console()
    client = get_api_client()
    
    try:
        response = client.post(f"/users/{user}/roles/{role}", json={})
        
        if response.status_code == 200:
            console.print(f"[green]Role '{role}' attached to user '{user}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] User or role not found")
        elif response.status_code == 409:
            console.print(f"[red]Error:[/red] Role already assigned to this user")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def attach_team_role(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    role: str = typer.Option(..., "--role", "-r", help="Role name or ID")
):
    """Attach a role to a team (inherited by all members)."""
    from rich.console import Console
    from src.api_client import get_api_client
    import httpx
    
    console = Console()
    client = get_api_client()
    
    try:
        # First get team ID from name
        response = client.get("/teams")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load teams")
            return
        
        teams = response.json()
        team_obj = next((t for t in teams if t["name"] == team), None)
        
        if not team_obj:
            console.print(f"[red]Error:[/red] Team '{team}' not found")
            return
            
        # Assign role
        response = client.post(f"/teams/{team_obj['id']}/roles/{role}", json={})
        
        if response.status_code == 200:
            console.print(f"[green]Role '{role}' attached to team '{team}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Team or role not found")
        elif response.status_code == 409:
            console.print(f"[red]Error:[/red] Role already assigned to this team")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def attach_role_policy(
    role: str = typer.Option(..., "--role", "-r", help="Role name or ID"),
    policy: str = typer.Option(..., "--policy", "-p", help="Policy name or ID")
):
    """Attach a policy to a role."""
    from rich.console import Console
    from src.api_client import get_api_client
    import httpx
    
    console = Console()
    client = get_api_client()
    
    try:
        response = client.post(f"/roles/{role}/policies/{policy}", json={})
        
        if response.status_code == 200:
            console.print(f"[green]Policy '{policy}' attached to role '{role}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Role or policy not found")
        elif response.status_code == 409:
            console.print(f"[red]Error:[/red] Policy already attached to this role")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def detach_role_policy(
    role: str = typer.Option(..., "--role", "-r", help="Role name or ID"),
    policy: str = typer.Option(..., "--policy", "-p", help="Policy name or ID")
):
    """Detach a policy from a role."""
    from rich.console import Console
    from src.api_client import get_api_client
    import httpx
    
    console = Console()
    client = get_api_client()
    
    try:
        response = client.delete(f"/roles/{role}/policies/{policy}")
        
        if response.status_code == 204:
            console.print(f"[green]Policy '{policy}' detached from role '{role}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Role, policy, or attachment not found")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def detach_user_role(
    user: str = typer.Option(..., "--user", "-u", help="Username or user ID"),
    role: str = typer.Option(..., "--role", "-r", help="Role name or ID")
):
    """Detach a role from a user."""
    from rich.console import Console
    from src.api_client import get_api_client
    import httpx
    
    console = Console()
    client = get_api_client()
    
    try:
        response = client.delete(f"/users/{user}/roles/{role}")
        
        if response.status_code == 204:
            console.print(f"[green]Role '{role}' detached from user '{user}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] User, role, or assignment not found")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def detach_team_role(
    team: str = typer.Option(..., "--team", "-t", help="Team name or ID"),
    role: str = typer.Option(..., "--role", "-r", help="Role name or ID")
):
    """Detach a role from a team."""
    from rich.console import Console
    from src.api_client import get_api_client
    import httpx
    
    console = Console()
    client = get_api_client()
    
    try:
        response = client.delete(f"/teams/{team}/roles/{role}")
        
        if response.status_code == 204:
            console.print(f"[green]Role '{role}' detached from team '{team}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Team, role, or assignment not found")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def edit(
    resource_type: str = typer.Argument(..., help="Resource type (role/roles, policy/policies, team/teams, user/users, workspace/ws, agent/agents, workflow/wf)"),
    identifier: Optional[str] = typer.Argument(None, help="Resource identifier (name or ID) - omit to edit all")
):
    """Edit resource(s) in your default editor (like kubectl edit)."""
    import os
    import tempfile
    import subprocess
    import yaml
    from rich.console import Console
    from src.api_client import get_api_client
    import httpx
    
    console = Console()
    client = get_api_client()
    
    resource_type = normalize_resource_type(resource_type)
    
    # Map resource types to endpoints
    singular_map = {
        "role": "/roles",
        "policy": "/policies",
        "team": "/teams",
        "user": "/users",
        "workspace": "/workspaces",
        "agent": "/agents",
        "workflow": "/workflows"
    }
    
    plural_map = {
        "roles": "/roles",
        "policies": "/policies",
        "teams": "/teams",
        "users": "/users",
        "workspaces": "/workspaces",
        "agents": "/agents",
        "workflows": "/workflows"
    }
    
    is_plural = resource_type in plural_map
    
    # If plural and no identifier, edit all resources
    if is_plural and not identifier:
        endpoint = plural_map[resource_type]
        
        try:
            # Fetch all resources
            response = client.get(endpoint)
            
            if response.status_code == 401:
                console.print("[red]Error:[/red] Not authenticated. Please login first.")
                return
            
            if response.status_code != 200:
                try:
                    error_detail = response.json().get('detail', response.text)
                except:
                    error_detail = response.text
                console.print(f"[red]Error:[/red] Could not fetch {resource_type}: {error_detail}")
                return
            
            resources_data = response.json()
            
            # Remove IDs and timestamps from all resources
            from src.utils import remove_ids_recursive
            clean_data = []
            for item in resources_data:
                # Remove IDs recursively and also remove timestamp fields
                clean_item = {k: remove_ids_recursive(v) for k, v in item.items() 
                             if k not in ['id', 'created_at', 'updated_at', 'team_id', 'user_id', 'role_id', 'policy_id', 'owner_id', 'workspace_id', 'assigned_at', 'joined_at']}
                clean_data.append(clean_item)
            
            # Create a temp file with YAML content
            editor = os.environ.get('EDITOR', 'vim')
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf:
                temp_path = tf.name
                yaml.dump(clean_data, tf, default_flow_style=False, sort_keys=False)
            
            try:
                # Open editor
                subprocess.call([editor, temp_path])
                
                # Read back the edited content
                with open(temp_path, 'r') as f:
                    lines = [line for line in f.readlines() if not line.strip().startswith('#')]
                    edited_data = yaml.safe_load(''.join(lines))
                
                if edited_data == clean_data:
                    console.print("[yellow]No changes made.[/yellow]")
                    return
                
                console.print("[yellow]Note:[/yellow] Bulk updates not yet implemented. Use single resource edit for now.")
                
            finally:
                os.unlink(temp_path)
                
        except httpx.ConnectError:
            console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
        return
    
    # Single resource edit
    if not identifier:
        console.print(f"[red]Error:[/red] Please specify a {resource_type} name/ID or use plural form to edit all")
        return
    
    endpoint = singular_map.get(resource_type, plural_map.get(resource_type))
    if not endpoint:
        console.print(f"[red]Error:[/red] Unknown resource type: {resource_type}")
        console.print("Valid types: role/roles, policy/policies, team/teams, user/users, workspace/ws, agent/agents, workflow/wf")
        return
    
    try:
        # Fetch the resource
        response = client.get(f"{endpoint}/{identifier}")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            try:
                error_detail = response.json().get('detail', response.text)
            except:
                error_detail = response.text
            console.print(f"[red]Error:[/red] Could not fetch {resource_type}: {error_detail}")
            return
        
        resource_data = response.json()
        
        # Remove IDs and timestamps
        from src.utils import remove_ids_recursive
        clean_data = {k: remove_ids_recursive(v) for k, v in resource_data.items() 
                     if k not in ['id', 'created_at', 'updated_at', 'team_id', 'user_id', 'role_id', 'policy_id', 'owner_id', 'workspace_id', 'assigned_at', 'joined_at']}
        
        # Create a temp file with YAML content
        editor = os.environ.get('EDITOR', 'vim')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf:
            temp_path = tf.name
            yaml.dump(clean_data, tf, default_flow_style=False, sort_keys=False)
        
        try:
            # Open editor
            subprocess.call([editor, temp_path])
            
            # Read back the edited content
            with open(temp_path, 'r') as f:
                lines = [line for line in f.readlines() if not line.strip().startswith('#')]
                edited_data = yaml.safe_load(''.join(lines))
            
            if edited_data == clean_data:
                console.print("[yellow]No changes made.[/yellow]")
                return
            
            # Send update to API
            response = client.put(f"{endpoint}/{identifier}", json=edited_data)
            
            if response.status_code == 200:
                console.print(f"[green]{resource_type.title()} '{identifier}' updated successfully![/green]")
            else:
                try:
                    error_detail = response.json().get('detail', response.text)
                except:
                    error_detail = response.text
                console.print(f"[red]Error updating {resource_type}:[/red] {error_detail}")
                
        finally:
            os.unlink(temp_path)
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def get(
    resource_type: str = typer.Argument(..., help="Resource type (role/roles, team/teams, user/users, policy/policies, workspace/ws, agent/agents, workflow/wf, run/runs, tool/tools)"),
    identifier: Optional[str] = typer.Argument(None, help="Resource identifier (name or ID) - omit to list all"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml, wide")
):
    """Get details of a specific resource or list all resources."""
    # Handle output format
    if output and output.lower() != "wide":
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            typer.echo(f"Invalid output format: {output}")
            typer.echo("Valid formats: json, yaml, wide")
            raise typer.Exit(1)
    
    resource_type = normalize_resource_type(resource_type)
    
    # Convert output string to OutputFormat for functions that need it
    output_format = None
    if output and output.lower() != "wide":
        try:
            output_format = OutputFormat(output.lower())
        except ValueError:
            pass
    
    # Handle plural forms for listing
    if resource_type == "roles":
        if identifier:
            from src.commands.role import show_role
            show_role(identifier, output_format)
        else:
            from src.commands.role import list_roles
            list_roles(output=output_format)
    elif resource_type == "role":
        if not identifier:
            from src.commands.role import list_roles
            list_roles(output=output_format)
        else:
            from src.commands.role import show_role
            show_role(identifier, output_format)
    elif resource_type == "teams":
        if identifier:
            from src.commands.team import show_team
            show_team(identifier, output_format)
        else:
            from src.commands.team import list_teams
            list_teams(output=output_format)
    elif resource_type == "team":
        if not identifier:
            from src.commands.team import list_teams
            list_teams(output=output_format)
        else:
            from src.commands.team import show_team
            show_team(identifier, output_format)
    elif resource_type == "policies":
        if identifier:
            from src.commands.policy import show_policy
            show_policy(identifier, output_format)
        else:
            from src.commands.policy import list_policies
            list_policies(output=output_format)
    elif resource_type == "policy":
        if not identifier:
            from src.commands.policy import list_policies
            list_policies(output=output_format)
        else:
            from src.commands.policy import show_policy
            show_policy(identifier, output_format)
    elif resource_type == "users":
        if identifier:
            from src.commands.user import show_user
            show_user(identifier, output_format)
        else:
            from src.commands.user import list_users
            list_users(output=output)
    elif resource_type == "user":
        from src.commands.user import show_user, me
        if not identifier:
            me(output_format)
        else:
            show_user(identifier, output_format)
    elif resource_type == "workspaces":
        if identifier:
            from src.commands.workspace import show_workspace
            show_workspace(identifier, output_format)
        else:
            from src.commands.workspace import list_workspaces
            list_workspaces(output=output_format)
    elif resource_type == "workspace":
        if not identifier:
            from src.commands.workspace import list_workspaces
            list_workspaces(output=output_format)
        else:
            from src.commands.workspace import show_workspace
            show_workspace(identifier, output_format)
    # Agent handling
    elif resource_type in ["agent", "agents"]:
        if identifier:
            from src.commands.agent import show_agent
            show_agent(identifier, output=output)
        else:
            from src.commands.agent import list_agents
            list_agents(output=output)
    # Workflow handling
    elif resource_type in ["workflow", "workflows"]:
        if identifier:
            from src.commands.workflow import show_workflow
            show_workflow(identifier, output=output)
        else:
            from src.commands.workflow import list_workflows
            list_workflows(output=output)
    # Run handling
    elif resource_type in ["run", "runs"]:
        if identifier:
            from src.commands.run import show_run
            show_run(identifier, output=output)
        else:
            from src.commands.run import list_runs
            list_runs(output=output)
    # Tool handling
    elif resource_type in ["tool", "tools"]:
        if identifier:
            from src.commands.tool import show_tool
            show_tool(identifier, output=output)
        else:
            from src.commands.tool import list_tools
            list_tools(output=output)
    else:
        typer.echo(f"Unknown resource type: {resource_type}")
        typer.echo("Valid types: role/roles, team/teams, workspace/ws, user/users, policy/policies, agent/agents, workflow/wf, run/runs, tool/tools")
        raise typer.Exit(1)

# ============= Export & Deploy Commands =============

@app.command(name="export-all")
def export_all(
    output_dir: str = typer.Option("aegis-export", "--output", "-o", help="Output directory"),
    include_docker: bool = typer.Option(True, "--docker/--no-docker", help="Include Docker Compose"),
    include_k8s: bool = typer.Option(False, "--k8s", help="Include Kubernetes manifests")
):
    """Export all agents and workflows to YAML files for deployment."""
    import os
    import yaml
    from rich.console import Console
    from src.api_client import get_api_client
    
    console = Console()
    client = get_api_client()
    
    os.makedirs(output_dir, exist_ok=True)
    agents_dir = os.path.join(output_dir, "agents")
    workflows_dir = os.path.join(output_dir, "workflows")
    os.makedirs(agents_dir, exist_ok=True)
    os.makedirs(workflows_dir, exist_ok=True)
    
    try:
        # Export agents
        agents_response = client.list_agents()
        agents = []
        if agents_response.status_code == 200:
            agents = agents_response.json()
            for agent in agents:
                from src.commands.agent import _export_agent_to_yaml
                file_path = os.path.join(agents_dir, f"{agent['name']}.yaml")
                _export_agent_to_yaml(agent, file_path)
                console.print(f"[green]Agent:[/green] {agent['name']}")
        
        # Export workflows
        workflows_response = client.list_workflows()
        workflows = []
        if workflows_response.status_code == 200:
            workflows = workflows_response.json()
            for wf in workflows:
                from src.commands.workflow import _export_workflow_to_yaml
                file_path = os.path.join(workflows_dir, f"{wf['name']}.yaml")
                _export_workflow_to_yaml(wf, file_path)
                console.print(f"[green]Workflow:[/green] {wf['name']}")
        
        # Generate Docker Compose if requested
        if include_docker:
            docker_compose = _generate_docker_compose(agents, workflows)
            docker_path = os.path.join(output_dir, "docker-compose.yml")
            with open(docker_path, "w") as f:
                yaml.dump(docker_compose, f, default_flow_style=False, sort_keys=False)
            console.print(f"[green]Docker Compose:[/green] {docker_path}")
        
        # Generate Kubernetes manifests if requested
        if include_k8s:
            k8s_dir = os.path.join(output_dir, "kubernetes")
            os.makedirs(k8s_dir, exist_ok=True)
            
            # Generate deployment and configmaps
            _generate_k8s_manifests(agents, workflows, k8s_dir)
            console.print(f"[green]Kubernetes:[/green] {k8s_dir}/")
        
        # Generate README
        readme_content = _generate_deployment_readme(output_dir, include_docker, include_k8s)
        with open(os.path.join(output_dir, "README.txt"), "w") as f:
            f.write(readme_content)
        
        console.print(f"\n[bold green]Export complete![/bold green]")
        console.print(f"  Agents: {len(agents)}")
        console.print(f"  Workflows: {len(workflows)}")
        console.print(f"  Location: {output_dir}/")
        
    except Exception as e:
        console.print(f"[red]Error during export:[/red] {e}")


def _generate_docker_compose(agents: list, workflows: list) -> dict:
    """Generate Docker Compose file for deployment."""
    return {
        "version": "3.8",
        "services": {
            "aegis-service": {
                "image": "aegis-service:latest",
                "ports": ["8000:8000"],
                "environment": {
                    "DB_HOST": "postgres",
                    "DB_PORT": "5432",
                    "DB_NAME": "agentic_ops",
                    "DB_USER": "aegis_app",
                    "DB_PASSWORD": "${DB_PASSWORD:-password123}",
                    "OPENAI_API_KEY": "${OPENAI_API_KEY}",
                    "GEMINI_API_KEY": "${GEMINI_API_KEY}",
                },
                "volumes": [
                    "./agents:/app/agents:ro",
                    "./workflows:/app/workflows:ro"
                ],
                "depends_on": ["postgres"],
                "restart": "unless-stopped"
            },
            "postgres": {
                "image": "postgres:15-alpine",
                "environment": {
                    "POSTGRES_DB": "agentic_ops",
                    "POSTGRES_USER": "aegis_app",
                    "POSTGRES_PASSWORD": "${DB_PASSWORD:-password123}"
                },
                "volumes": ["postgres_data:/var/lib/postgresql/data"],
                "restart": "unless-stopped"
            }
        },
        "volumes": {
            "postgres_data": {}
        }
    }


def _generate_k8s_manifests(agents: list, workflows: list, output_dir: str):
    """Generate Kubernetes manifests."""
    import yaml
    import os
    
    # Namespace
    namespace = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": "aegis"}
    }
    
    # ConfigMap with agent configs
    agent_configs = {name: agent for name, agent in [(a["name"], a) for a in agents]}
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": "aegis-agents-config",
            "namespace": "aegis"
        },
        "data": {
            "agents.json": yaml.dump(agent_configs)
        }
    }
    
    # Deployment
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "aegis-service",
            "namespace": "aegis"
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "aegis-service"}},
            "template": {
                "metadata": {"labels": {"app": "aegis-service"}},
                "spec": {
                    "containers": [{
                        "name": "aegis-service",
                        "image": "aegis-service:latest",
                        "ports": [{"containerPort": 8000}],
                        "envFrom": [{"secretRef": {"name": "aegis-secrets"}}],
                        "volumeMounts": [{
                            "name": "agents-config",
                            "mountPath": "/app/config"
                        }]
                    }],
                    "volumes": [{
                        "name": "agents-config",
                        "configMap": {"name": "aegis-agents-config"}
                    }]
                }
            }
        }
    }
    
    # Service
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "aegis-service",
            "namespace": "aegis"
        },
        "spec": {
            "selector": {"app": "aegis-service"},
            "ports": [{"port": 8000, "targetPort": 8000}],
            "type": "ClusterIP"
        }
    }
    
    # Write manifests
    with open(os.path.join(output_dir, "namespace.yaml"), "w") as f:
        yaml.dump(namespace, f)
    
    with open(os.path.join(output_dir, "configmap.yaml"), "w") as f:
        yaml.dump(configmap, f)
    
    with open(os.path.join(output_dir, "deployment.yaml"), "w") as f:
        yaml.dump(deployment, f)
    
    with open(os.path.join(output_dir, "service.yaml"), "w") as f:
        yaml.dump(service, f)


def _generate_deployment_readme(output_dir: str, docker: bool, k8s: bool) -> str:
    """Generate README for deployment."""
    content = """AEGIS DEPLOYMENT EXPORT
======================

This directory contains exported agents and workflows from your Aegis instance.

STRUCTURE
---------
agents/      - Agent YAML definitions
workflows/   - Workflow YAML definitions
"""
    
    if docker:
        content += """
docker-compose.yml - Docker Compose deployment

DOCKER DEPLOYMENT
-----------------
1. Set environment variables:
   export DB_PASSWORD=your_password
   export OPENAI_API_KEY=your_key
   export GEMINI_API_KEY=your_key

2. Start services:
   docker-compose up -d

3. Access API at http://localhost:8000
"""
    
    if k8s:
        content += """
kubernetes/  - Kubernetes manifests

KUBERNETES DEPLOYMENT
---------------------
1. Create secrets:
   kubectl create secret generic aegis-secrets \\
     --from-literal=DB_PASSWORD=your_password \\
     --from-literal=OPENAI_API_KEY=your_key

2. Apply manifests:
   kubectl apply -f kubernetes/

3. Port forward to access:
   kubectl port-forward svc/aegis-service 8000:8000 -n aegis
"""
    
    content += """
IMPORTING AGENTS
----------------
To import agents into a new Aegis instance:
  aegis agent import agents/my-agent.yaml
  
Or apply all:
  aegis agent apply agents/ -r

For help: aegis --help
"""
    return content


# ============= Config Commands =============

@app.command(name="config")
def config_cmd(
    key: Optional[str] = typer.Argument(None, help="Config key to get/set (api_url, output_format)"),
    value: Optional[str] = typer.Argument(None, help="Value to set"),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all config values")
):
    """View or modify CLI configuration."""
    from rich.console import Console
    from src.config import load_config, save_config, get_api_url, set_api_url, set_default_output_format, get_default_output_format
    
    console = Console()
    
    if show_all or (key is None and value is None):
        # Show all config
        config = load_config()
        console.print("\n[bold cyan]Aegis CLI Configuration[/bold cyan]\n")
        console.print(f"[bold]API URL:[/bold] {get_api_url()}")
        console.print(f"[bold]Output Format:[/bold] {get_default_output_format()}")
        console.print(f"[bold]Auth Token:[/bold] {'[green]Set[/green]' if config.get('auth_token') else '[yellow]Not set[/yellow]'}")
        console.print(f"\n[dim]Config file: ~/.aegis/config[/dim]")
        return
    
    if key and value is None:
        # Get specific key
        config = load_config()
        if key == "api_url":
            console.print(f"{get_api_url()}")
        elif key == "output_format":
            console.print(f"{get_default_output_format()}")
        elif key in config:
            console.print(f"{config[key]}")
        else:
            console.print(f"[yellow]Config key '{key}' not found[/yellow]")
        return
    
    if key and value:
        # Set specific key
        if key == "api_url":
            set_api_url(value)
            console.print(f"[green]API URL set to: {value}[/green]")
        elif key == "output_format":
            if value.lower() in ["text", "json", "yaml", "table"]:
                set_default_output_format(value.lower())
                console.print(f"[green]Default output format set to: {value}[/green]")
            else:
                console.print("[red]Invalid output format. Use: text, json, yaml, or table[/red]")
        else:
            config = load_config()
            config[key] = value
            save_config(config)
            console.print(f"[green]Config '{key}' set to: {value}[/green]")


@app.command(name="logout")
def logout():
    """Clear authentication and logout."""
    from rich.console import Console
    from src.config import clear_auth
    
    console = Console()
    clear_auth()
    console.print("[green]Logged out successfully.[/green]")


@app.command(name="whoami")
def whoami():
    """Show current authenticated user."""
    from src.commands.user import me
    me(output=None)


# ============= Convenience Commands =============

@app.command(name="run-agent")
def run_agent_quick(
    agent: str = typer.Argument(..., help="Agent name or ID"),
    message: str = typer.Argument(..., help="Input message"),
    wait: bool = typer.Option(False, "-w", "--wait", help="Wait for completion"),
    context: Optional[str] = typer.Option(None, "-c", "--context", help="Context variables as JSON")
):
    """Quick command to run an agent."""
    from src.commands.agent import run as agent_run
    agent_run(agent, message, context=context, wait=wait)


@app.command(name="run-workflow")
def run_workflow_quick(
    workflow: str = typer.Argument(..., help="Workflow name or ID"),
    message: str = typer.Argument(..., help="Input message"),
    wait: bool = typer.Option(False, "-w", "--wait", help="Wait for completion"),
    context: Optional[str] = typer.Option(None, "-c", "--context", help="Context variables as JSON")
):
    """Quick command to run a workflow."""
    from src.commands.workflow import run as workflow_run
    workflow_run(workflow, message, context=context, wait=wait)


@app.command(name="stats")
def show_stats(
    days: int = typer.Option(30, "-d", "--days", help="Number of days for statistics"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Output format: json, yaml")
):
    """Show run statistics summary."""
    from src.commands.run import stats as run_stats
    run_stats(days=days, output=output)


@app.command(name="watch")
def watch_run(
    run_id: str = typer.Argument(..., help="Run ID to watch"),
    interval: int = typer.Option(2, "-i", "--interval", help="Poll interval in seconds")
):
    """Watch a run until completion."""
    from src.commands.run import watch as run_watch
    run_watch(run_id, interval=interval)


@app.command(name="cancel")
def cancel_run(
    run_id: str = typer.Argument(..., help="Run ID to cancel"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation")
):
    """Cancel a running execution."""
    from src.commands.run import cancel as run_cancel
    run_cancel(run_id, yes=yes)


@app.command(name="logs")
def show_logs(
    run_id: str = typer.Argument(..., help="Run ID"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow logs in real-time"),
    tail: int = typer.Option(100, "-n", "--tail", help="Number of lines to show")
):
    """Show logs for a run (messages and tool calls)."""
    from src.commands.run import logs as run_logs
    run_logs(run_id, follow=follow, tail=tail)


# Set up error handling at module level
import sys
import os
from click.exceptions import NoSuchOption, BadParameter, MissingParameter

def _generate_error_message(cmd: str, args: list) -> str:
    """Generate dynamic error message based on command and arguments."""
    # Command expectations
    cmd_expectations = {
        'edit': {
            'required_args': 1,
            'optional_args': 1,
            'total_args': 2,
            'expected': '<resource_type> [identifier]',
            'no_options': True
        },
        'create': {
            'required_args': 2,
            'optional_args': 0,
            'total_args': 2,
            'expected': '<resource_type> <name> [options]'
        },
        'delete': {
            'required_args': 2,
            'optional_args': 0,
            'total_args': 2,
            'expected': '<resource_type> <identifier>'
        },
        'get': {
            'required_args': 1,
            'optional_args': 1,
            'total_args': 2,
            'expected': '<resource_type> [identifier] [--output <format>]'
        }
    }
    
    if cmd not in cmd_expectations:
        return f"Error: {str(args)}"
    
    exp = cmd_expectations[cmd]
    
    # Find command position in args
    try:
        cmd_idx = args.index(cmd)
        cmd_args = args[cmd_idx + 1:]
    except ValueError:
        return f"Error: Invalid command or arguments"
    
    # Count positional arguments (non-option arguments)
    positional_args = [arg for arg in cmd_args if not arg.startswith('-')]
    options = [arg for arg in cmd_args if arg.startswith('-')]
    
    # Check for invalid options
    if exp.get('no_options') and options:
        invalid_option = options[0]
        return f"Error: Invalid option '{invalid_option}' for '{cmd}' command. Expected arguments: {exp['expected']}"
    
    # Check argument count
    if len(positional_args) < exp['required_args']:
        return f"Error: Missing required argument(s) for '{cmd}' command. Expected: {exp['expected']}, got: {len(positional_args)} argument(s)"
    elif len(positional_args) > exp['total_args']:
        return f"Error: Too many arguments for '{cmd}' command. Expected: {exp['expected']}, got: {len(positional_args)} argument(s)"
    
    # Generic error
    return f"Error: Invalid arguments for '{cmd}' command. Expected: {exp['expected']}"

# Patch Typer's Rich error handler to suppress traceback and colors for errors
try:
    import typer.rich_utils
    from click.exceptions import NoSuchOption
    
    _original_rich_format_error = typer.rich_utils.rich_format_error
    
    def _patched_rich_format_error(exc: Exception, *args, **kwargs):
        """Patch Rich error formatting to suppress traceback and colors for errors."""
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd in ['edit', 'create', 'delete', 'get']:
                exc_str = str(exc)
                if (isinstance(exc, (TypeError, NoSuchOption)) or 
                    'takes' in exc_str or 
                    'No such option' in exc_str or
                    'Missing argument' in exc_str or
                    'Got unexpected extra' in exc_str):
                    error_msg = _generate_error_message(cmd, sys.argv)
                    # Use plain print without Rich formatting
                    print(error_msg, file=sys.stderr)
                    sys.exit(1)
        # For other errors, also suppress Rich formatting
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd in ['edit', 'create', 'delete', 'get']:
                error_msg = _generate_error_message(cmd, sys.argv)
                print(error_msg, file=sys.stderr)
                sys.exit(1)
        return _original_rich_format_error(exc, *args, **kwargs)
    
    typer.rich_utils.rich_format_error = _patched_rich_format_error
except (ImportError, AttributeError):
    pass

# Custom exception handler to catch errors during Typer's error formatting
_original_excepthook = sys.excepthook

def _custom_excepthook(exc_type, exc_value, exc_traceback):
    """Custom exception handler to provide clean error messages without colors."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in ['edit', 'create', 'delete', 'get']:
            if exc_type == TypeError or 'takes' in str(exc_value) or 'No such option' in str(exc_value):
                error_msg = _generate_error_message(cmd, sys.argv)
                print(error_msg, file=sys.stderr)
                sys.exit(1)
    # For other errors, use original handler
    _original_excepthook(exc_type, exc_value, exc_traceback)

sys.excepthook = _custom_excepthook

# Override app's __call__ to add validation
_original_app_call = app.__call__

def _app_call_wrapper(*args, **kwargs):
    """Wrapper for app() call that validates arguments."""
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in ['edit', 'create', 'delete', 'get']:
            # Check for invalid options before Typer parses
            cmd_expectations = {
                'edit': {'no_options': True},
                'create': {'no_options': False},
                'delete': {'no_options': True},
                'get': {'no_options': False}
            }
            if cmd_expectations.get(cmd, {}).get('no_options'):
                cmd_idx = sys.argv.index(cmd)
                cmd_args = sys.argv[cmd_idx + 1:]
                options = [arg for arg in cmd_args if arg.startswith('-')]
                if options:
                    error_msg = _generate_error_message(cmd, sys.argv)
                    print(error_msg, file=sys.stderr)
                    sys.exit(1)
    
    try:
        return _original_app_call(*args, **kwargs)
    except (NoSuchOption, BadParameter) as e:
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd in ['edit', 'create', 'delete', 'get']:
                error_msg = _generate_error_message(cmd, sys.argv)
                print(error_msg, file=sys.stderr)
                sys.exit(1)
        # Re-raise other exceptions to show normal error
        raise
    except MissingParameter as e:
        # Handle missing required arguments with better error messages
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            error_msg = _generate_error_message(cmd, sys.argv)
            print(error_msg, file=sys.stderr)
            sys.exit(1)
        raise
    except TypeError as e:
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd in ['edit', 'create', 'delete', 'get']:
                if 'takes' in str(e) or 'positional argument' in str(e):
                    error_msg = _generate_error_message(cmd, sys.argv)
                    print(error_msg, file=sys.stderr)
                    sys.exit(1)
        # For other TypeErrors, re-raise
        raise
    except Exception as e:
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd in ['edit', 'create', 'delete', 'get']:
                if 'takes' in str(e) or 'No such option' in str(e):
                    error_msg = _generate_error_message(cmd, sys.argv)
                    print(error_msg, file=sys.stderr)
                    sys.exit(1)
        raise

app.__call__ = _app_call_wrapper

if __name__ == "__main__":
    app()
