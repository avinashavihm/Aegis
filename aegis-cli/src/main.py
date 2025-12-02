import typer
from typing import Optional
from src.commands import user, team, role, policy, workspace
from src.commands.user import login
from src.utils import OutputFormat, set_output_format

app = typer.Typer(
    name="aegis",
    help="Agentic Ops CLI Tool",
    add_completion=False,
    no_args_is_help=True
)

@app.callback()
def main(
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format: json, yaml, wide. Default: text"
    )
):
    """
    Aegis CLI - Agentic Ops Platform
    """
    if output is None:
        from src.config import get_default_output_format
        output = OutputFormat(get_default_output_format())
        set_output_format(output)
    elif output.lower() != "wide":
        # Only set format if not wide (wide is handled per-command)
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            pass  # Will be handled by individual commands

app.add_typer(user.app, name="user", help="Manage users")
app.add_typer(team.app, name="team", help="Manage teams")
app.add_typer(role.app, name="role", help="Manage roles")
app.add_typer(policy.app, name="policy", help="Manage policies")
app.add_typer(workspace.app, name="workspace", help="Manage workspaces (for agents & workflows)")
app.command()(login)

# Import and add change-password as top-level command
from src.commands.user import change_password
app.command(name="change-password")(change_password)

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
def edit(
    resource_type: str = typer.Argument(..., help="Resource type (role/roles, policy/policies, team/teams, user/users)"),
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
    
    # Map resource types to endpoints
    singular_map = {
        "role": "/roles",
        "policy": "/policies",
        "team": "/teams",
        "user": "/users"
    }
    
    plural_map = {
        "roles": "/roles",
        "policies": "/policies",
        "teams": "/teams",
        "users": "/users"
    }
    
    resource_type = resource_type.lower()
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
            clean_data = []
            for item in resources_data:
                clean_item = {k: v for k, v in item.items() 
                             if k not in ['id', 'created_at', 'updated_at', 'team_id', 'user_id', 'role_id', 'policy_id', 'owner_id']}
                clean_data.append(clean_item)
            
            # Create a temp file with YAML content
            editor = os.environ.get('EDITOR', 'vim')
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf:
                temp_path = tf.name
                tf.write(f"# Edit {resource_type}\n")
                tf.write(f"# Save and close to apply changes\n")
                tf.write(f"# You can modify, add, or remove items\n\n")
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
        console.print("Valid types: role/roles, policy/policies, team/teams, user/users")
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
        clean_data = {k: v for k, v in resource_data.items() 
                     if k not in ['id', 'created_at', 'updated_at', 'team_id', 'user_id', 'role_id', 'policy_id', 'owner_id']}
        
        # Create a temp file with YAML content
        editor = os.environ.get('EDITOR', 'vim')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf:
            temp_path = tf.name
            tf.write(f"# Edit {resource_type}: {identifier}\n")
            tf.write(f"# Save and close to apply changes\n\n")
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
    resource_type: str = typer.Argument(..., help="Resource type (role/roles, team/teams, user/users, policy/policies)"),
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
    
    resource_type = resource_type.lower()
    
    # Normalize shorthand aliases
    alias_map = {
        "ws": "workspaces",  # ws = workspace (different from teams - for agents & workflows)
        "wss": "workspaces",
        "workspace": "workspaces",
        "workspaces": "workspaces",
        "teams": "teams",
        "team": "team",
        "policies": "policies",
        "policy": "policy"
    }
    resource_type = alias_map.get(resource_type, resource_type)
    
    # Handle plural forms for listing
    if resource_type == "roles":
        from src.commands.role import list_roles
        list_roles(team_name=None, output=output)
    elif resource_type == "role":
        if not identifier:
            # Default to listing all roles
            from src.commands.role import list_roles
            list_roles(team_name=None, output=output)
        else:
            from src.commands.role import show_role
            show_role(identifier, output)
    elif resource_type == "teams":
        from src.commands.team import list_teams
        list_teams(output=output)
    elif resource_type == "team":
        if not identifier:
            # Default to listing all teams
            from src.commands.team import list_teams
            list_teams(output=output)
        else:
            from src.commands.team import show_team
            show_team(identifier, output)
    elif resource_type == "policies":
        from src.commands.policy import list_policies
        list_policies(output=output)
    elif resource_type == "policy":
        if not identifier:
            # Default to listing all policies
            from src.commands.policy import list_policies
            list_policies(output=output)
        else:
            from src.commands.policy import show_policy
            show_policy(identifier, output)
    elif resource_type == "users":
        from src.commands.user import list_users
        list_users(output=output)
    elif resource_type == "user":
        from src.commands.user import show_user, me
        if not identifier:
            # Default to current user
            me(output)
        else:
            show_user(identifier, output)
    elif resource_type == "workspaces":
        from src.commands.workspace import list_workspaces
        # Convert output format if needed
        output_format = None
        if output:
            try:
                output_format = OutputFormat(output.lower())
            except ValueError:
                pass
        list_workspaces(output=output_format)
    elif resource_type == "workspace":
        if not identifier:
            # Default to listing all workspaces
            from src.commands.workspace import list_workspaces
            list_workspaces(output=output)
        else:
            from src.commands.workspace import show_workspace
            show_workspace(identifier, output)
    else:
        typer.echo(f"Unknown resource type: {resource_type}")
        typer.echo("Valid types: role/roles, team/teams, workspace/ws, user/users, policy/policies")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
