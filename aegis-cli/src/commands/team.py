import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from src.api_client import get_api_client
from src.config import get_context, set_context
from src.utils import OutputFormat, set_output_format
import httpx

app = typer.Typer()
console = Console()


@app.command()
def create(
    name: str
):
    """Create a new team."""
    client = get_api_client()
    
    # Enforce team name constraints
    import re
    if not re.match(r'^[a-z0-9-]+$', name):
        console.print("[red]Error:[/red] Name must contain only lowercase letters, numbers, and hyphens (no spaces).")
        return

    try:
        response = client.post("/teams", json={
            "name": name
        })
        
        if response.status_code == 201:
            team = response.json()
            console.print(f"[green]Team created successfully![/green] ID: {team['id']}")
            
            # Auto-set context
            set_context(name)
            console.print(f"[blue]Context set to team: {name}[/blue]")
        elif response.status_code == 400:
            console.print(f"[red]Error:[/red] {response.json()['detail']}")
        elif response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error creating team:[/red] {e}")


def list_teams(
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List all teams."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get("/teams")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        teams = response.json()
        
        current_context = get_context()

        # Add current context indicator and format roles
        for t in teams:
            t[""] = "*" if t["name"] == current_context else ""
            # Rename id to team_id for display
            t["team_id"] = t["id"]
            # Format roles and members for display
            t["team_roles"] = ", ".join(t.get("team_roles", [])) or "-"
            t["members"] = ", ".join(t.get("members", [])) or "-"

        from src.utils import print_output, current_output_format, OutputFormat
        
        # For structured formats (JSON/YAML), remove IDs, slugs, and marker column
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_teams = []
            for t in teams:
                # Convert comma-separated strings back to lists
                team_roles_list = [r.strip() for r in t.get("team_roles", "").split(",") if r.strip()] if isinstance(t.get("team_roles"), str) else t.get("team_roles", [])
                members_list = [m.strip() for m in t.get("members", "").split(",") if m.strip()] if isinstance(t.get("members"), str) else t.get("members", [])
                
                clean_t = {
                    "name": t["name"],
                    "team_roles": team_roles_list,
                    "members": members_list
                }
                clean_teams.append(clean_t)
            print_output(
                clean_teams,
                title="Teams"
            )
        else:
            print_output(
                teams,
                columns=["name", "team_roles", "members"],
                title="Teams"
            )
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error listing teams:[/red] {e}")


@app.command(name="assign-role")
def assign_role(
    role: str = typer.Argument(..., help="Role name or ID to assign"),
    team_name: str = typer.Option(None, "--team", "-t", help="Team name (optional, uses current context)")
):
    """Assign a role to a team (inherited by all members)."""
    client = get_api_client()
    
    # Use current context if no team specified
    if not team_name:
        team_name = get_context()
        if not team_name:
            console.print("[red]Error:[/red] No team specified and no context set.")
            return

    try:
        # First get team ID from name
        response = client.get("/teams")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load teams")
            return
        
        teams = response.json()
        team = next((t for t in teams if t["name"] == team_name), None)
        
        if not team:
            console.print(f"[red]Error:[/red] Team '{team_name}' not found")
            return
            
        # Assign role
        response = client.post(f"/teams/{team['id']}/roles/{role}", json={})
        
        if response.status_code == 200:
            console.print(f"[green]Role '{role}' assigned to team '{team['name']}'.[/green]")
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


@app.command(name="remove-role")
def remove_role(
    role: str = typer.Argument(..., help="Role name or ID to remove"),
    team_name: str = typer.Option(None, "--team", "-t", help="Team name (optional, uses current context)")
):
    """Remove a role from a team."""
    client = get_api_client()
    
    # Use current context if no team specified
    if not team_name:
        team_name = get_context()
        if not team_name:
            console.print("[red]Error:[/red] No team specified and no context set.")
            return

    try:
        # First get team ID from name
        response = client.get("/teams")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load teams")
            return
        
        teams = response.json()
        team = next((t for t in teams if t["name"] == team_name), None)
        
        if not team:
            console.print(f"[red]Error:[/red] Team '{team_name}' not found")
            return
            
        if not typer.confirm(f"Remove role '{role}' from team '{team['name']}'?"):
            return

        # Remove role
        response = client.delete(f"/teams/{team['id']}/roles/{role}")
        
        if response.status_code == 204:
            console.print(f"[green]Role '{role}' removed from team '{team['name']}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Team, role, or assignment not found")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="set")
def set_team(name: str = typer.Argument(..., help="Team name")):
    """Set the current team context."""
    client = get_api_client()
    
    try:
        # Verify team exists and user has access
        response = client.get("/teams")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        teams = response.json()
        
        # Check if team exists by name
        team_exists = any(t["name"] == name for t in teams)
        
        if team_exists:
            set_context(name)
            console.print(f"[green]Context set to team: {name}[/green]")
        else:
            console.print(f"[red]Team '{name}' not found or you do not have access.[/red]")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error setting context:[/red] {e}")


@app.command(name="current")
def get_current_team():
    """Get the currently set team context."""
    context = get_context()
    if context:
        console.print(context)
    else:
        console.print("[yellow]No team context set.[/yellow]")


@app.command(name="members")
def list_members(
    team_name: str = typer.Argument(None, help="Team name (optional, uses current context if omitted)"),
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List members of a team."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    # Use current context if no team specified
    if not team_name:
        team_name = get_context()
        if not team_name:
            console.print("[red]Error:[/red] No team specified and no context set.")
            return
    
    try:
        # First get team ID from name
        response = client.get("/teams")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load teams")
            return
        
        teams = response.json()
        team = next((t for t in teams if t["name"] == team_name), None)
        
        if not team:
            console.print(f"[red]Error:[/red] Team '{team_name}' not found")
            return
        
        # Get members
        response = client.get(f"/teams/{team['id']}/members")
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        members = response.json()
        
        # Format timestamp
        for member in members:
            member["joined_at"] = member["joined_at"][:19]

        from src.utils import print_output
        print_output(
            members,
            columns=["username", "role_name", "joined_at"],
            title=f"Members of {team['name']}"
        )
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="add-member")
def add_member(
    username: str = typer.Argument(..., help="Username to add"),
    role: str = typer.Option("viewer", "--role", "-r", help="Role to assign"),
    team_name: str = typer.Option(None, "--team", "-t", help="Team name (optional, uses current context)")
):
    """Add a user to a team."""
    client = get_api_client()
    
    # Use current context if no team specified
    if not team_name:
        team_name = get_context()
        if not team_name:
            console.print("[red]Error:[/red] No team specified and no context set.")
            return

    try:
        # First get team ID from name
        response = client.get("/teams")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load teams")
            return
        
        teams = response.json()
        team = next((t for t in teams if t["name"] == team_name), None)
        
        if not team:
            console.print(f"[red]Error:[/red] Team '{team_name}' not found")
            return
            
        # Add member
        response = client.post(f"/teams/{team['id']}/members", json={
            "username": username,
            "role": role
        })
        
        if response.status_code == 200:
            console.print(f"[green]User '{username}' added to team '{team['name']}' with role '{role}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] User or role not found")
        elif response.status_code == 409:
            console.print(f"[red]Error:[/red] User is already a member of this team")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="remove-member")
def remove_member(
    username: str = typer.Argument(..., help="Username to remove"),
    team_name: str = typer.Option(None, "--team", "-t", help="Team name (optional, uses current context)")
):
    """Remove a user from a team."""
    client = get_api_client()
    
    # Use current context if no team specified
    if not team_name:
        team_name = get_context()
        if not team_name:
            console.print("[red]Error:[/red] No team specified and no context set.")
            return

    try:
        # First get team ID from name
        response = client.get("/teams")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load teams")
            return
        
        teams = response.json()
        team = next((t for t in teams if t["name"] == team_name), None)
        
        if not team:
            console.print(f"[red]Error:[/red] Team '{team_name}' not found")
            return
            
        # Resolve username to ID
        # We need a way to get user ID from username. 
        # The remove endpoint expects user_id.
        # Let's try to find the user in the member list first.
        
        response = client.get(f"/teams/{team['id']}/members")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load members")
            return
            
        members = response.json()
        member = next((m for m in members if m["username"] == username), None)
        
        if not member:
            console.print(f"[red]Error:[/red] User '{username}' is not a member of team '{team['name']}'")
            return
            
        if not typer.confirm(f"Remove user '{username}' from team '{team['name']}'?"):
            return

        # Remove member
        response = client.delete(f"/teams/{team['id']}/members/{member['user_id']}")
        
        if response.status_code == 204:
            console.print(f"[green]User '{username}' removed from team '{team['name']}'.[/green]")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def show_team(team_identifier: str, output: Optional[OutputFormat] = None):
    """Show team details by name or ID."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get(f"/teams/{team_identifier}")
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        team = response.json()
        
        from src.utils import current_output_format, print_output
        
        # For structured formats, output full data
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(team)
        else:
            # For text/table, show as single-row table with name first
            print_output(
                team,
                columns=["name", "id", "owner_id"]
            )
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
