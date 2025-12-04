import typer
from typing import Optional
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
        "ws": "workspace",
        "wss": "workspaces",
        "workspace": "workspace",
        "workspaces": "workspaces",
        "user": "user",
        "users": "users",
        "team": "team",
        "teams": "teams",
        "role": "role",
        "roles": "roles",
        "policy": "policy",
        "policies": "policies",
    }
    return alias_map.get(resource_type, resource_type)


@app.command()
def create(
    resource_type: str = typer.Argument(..., help="Resource type (user, team, role, policy, workspace/ws)"),
    name: str = typer.Argument(..., help="Resource name/identifier"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    email: Optional[str] = typer.Option(None, "--email", help="Email (for user)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password (for user)"),
    full_name: Optional[str] = typer.Option(None, "--name", help="Full name (for user)"),
    policy: Optional[str] = typer.Option(None, "--policy", help="Policy ID/name (for role)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="File path (for policy)"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Content JSON string (for policy)")
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
    else:
        typer.echo(f"[red]Error:[/red] Unknown resource type: {resource_type}")
        typer.echo("Valid types: user, team, role, policy, workspace/ws")
        raise typer.Exit(1)


@app.command()
def delete(
    resource_type: str = typer.Argument(..., help="Resource type (user, team, role, policy, workspace/ws)"),
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
    else:
        typer.echo(f"[red]Error:[/red] Unknown resource type: {resource_type}")
        typer.echo("Valid types: user, team, role, policy, workspace/ws")
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
    resource_type: str = typer.Argument(..., help="Resource type (role/roles, policy/policies, team/teams, user/users, workspace/ws)"),
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
        "workspace": "/workspaces"
    }
    
    plural_map = {
        "roles": "/roles",
        "policies": "/policies",
        "teams": "/teams",
        "users": "/users",
        "workspaces": "/workspaces"
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
        console.print("Valid types: role/roles, policy/policies, team/teams, user/users, workspace/ws")
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
    resource_type: str = typer.Argument(..., help="Resource type (role/roles, team/teams, user/users, policy/policies, workspace/ws)"),
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
            # If identifier provided with plural form, show single resource
            from src.commands.role import show_role
            show_role(identifier, output_format)
        else:
            from src.commands.role import list_roles
            list_roles(output=output_format)
    elif resource_type == "role":
        if not identifier:
            # Default to listing all roles
            from src.commands.role import list_roles
            list_roles(output=output_format)
        else:
            from src.commands.role import show_role
            show_role(identifier, output_format)
    elif resource_type == "teams":
        if identifier:
            # If identifier provided with plural form, show single resource
            from src.commands.team import show_team
            show_team(identifier, output_format)
        else:
            from src.commands.team import list_teams
            list_teams(output=output_format)
    elif resource_type == "team":
        if not identifier:
            # Default to listing all teams
            from src.commands.team import list_teams
            list_teams(output=output_format)
        else:
            from src.commands.team import show_team
            show_team(identifier, output_format)
    elif resource_type == "policies":
        if identifier:
            # If identifier provided with plural form, show single resource
            from src.commands.policy import show_policy
            show_policy(identifier, output_format)
        else:
            from src.commands.policy import list_policies
            list_policies(output=output_format)
    elif resource_type == "policy":
        if not identifier:
            # Default to listing all policies
            from src.commands.policy import list_policies
            list_policies(output=output_format)
        else:
            from src.commands.policy import show_policy
            show_policy(identifier, output_format)
    elif resource_type == "users":
        if identifier:
            # If identifier provided with plural form, show single resource
            from src.commands.user import show_user
            show_user(identifier, output_format)
        else:
            from src.commands.user import list_users
            list_users(output=output)
    elif resource_type == "user":
        from src.commands.user import show_user, me
        if not identifier:
            # Default to current user
            me(output_format)
        else:
            show_user(identifier, output_format)
    elif resource_type == "workspaces":
        if identifier:
            # If identifier provided with plural form, show single resource
            from src.commands.workspace import show_workspace
            show_workspace(identifier, output_format)
        else:
            from src.commands.workspace import list_workspaces
            list_workspaces(output=output_format)
    elif resource_type == "workspace":
        if not identifier:
            # Default to listing all workspaces
            from src.commands.workspace import list_workspaces
            list_workspaces(output=output_format)
        else:
            from src.commands.workspace import show_workspace
            show_workspace(identifier, output_format)
    else:
        typer.echo(f"Unknown resource type: {resource_type}")
        typer.echo("Valid types: role/roles, team/teams, workspace/ws, user/users, policy/policies")
        raise typer.Exit(1)

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
