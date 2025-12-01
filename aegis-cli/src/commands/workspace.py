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
    name: str,
    slug: str = typer.Option(None, "--slug", "-s", help="Unique slug for the workspace (auto-generated from name if omitted)")
):
    """Create a new workspace."""
    client = get_api_client()
    
    # Enforce slug-like behavior for name
    import re
    if not re.match(r'^[a-z0-9-]+$', name):
        console.print("[red]Error:[/red] Name must contain only lowercase letters, numbers, and hyphens (no spaces).")
        return

    try:
        # Use name as both name and slug
        response = client.post("/workspaces", json={
            "name": name,
            "slug": name
        })
        
        if response.status_code == 201:
            workspace = response.json()
            console.print(f"[green]Workspace created successfully![/green] ID: {workspace['id']}")
            
            # Auto-set context
            set_context(name)
            console.print(f"[blue]Context set to workspace: {name}[/blue]")
        elif response.status_code == 400:
            console.print(f"[red]Error:[/red] {response.json()['detail']}")
        elif response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error creating workspace:[/red] {e}")


@app.command(name="list")
@app.command(name="ls")
@app.command(name="get")
def list_workspaces(
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List all workspaces."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get("/workspaces")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        workspaces = response.json()
        
        current_context = get_context()

        # Add current context indicator
        for ws in workspaces:
            ws[""] = "*" if ws["slug"] == current_context else ""

        from src.utils import print_output, current_output_format, OutputFormat
        
        # For structured formats (JSON/YAML), remove the marker column
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            for ws in workspaces:
                ws.pop("", None)
            print_output(
                workspaces,
                columns=["name", "id", "owner_id"],
                title="Workspaces"
            )
        else:
            print_output(
                workspaces,
                columns=["", "name", "id", "owner_id"],
                title="Workspaces"
            )
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error listing workspaces:[/red] {e}")


@app.command(name="set")
def set_workspace(name: str = typer.Argument(..., help="Workspace name")):
    """Set the current workspace context."""
    client = get_api_client()
    
    try:
        # Verify workspace exists and user has access
        response = client.get("/workspaces")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        workspaces = response.json()
        
        # Try to find by slug first
        target_ws = next((ws for ws in workspaces if ws["slug"] == identifier), None)
        
        # If not found, try to find by name (case insensitive)
        if not target_ws:
            target_ws = next((ws for ws in workspaces if ws["name"].lower() == identifier.lower()), None)
            
        # Since name == slug now, we just check slug field (which stores the name)
        workspace_exists = any(ws["slug"] == name for ws in workspaces)
        
        if workspace_exists:
            set_context(name)
            console.print(f"[green]Context set to workspace: {name}[/green]")
        else:
            console.print(f"[red]Workspace '{name}' not found or you do not have access.[/red]")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error setting context:[/red] {e}")


@app.command(name="current")
def get_current_workspace():
    """Get the currently set workspace context."""
    context = get_context()
    if context:
        console.print(context)
    else:
        console.print("[yellow]No workspace context set.[/yellow]")


@app.command(name="members")
def list_members(
    workspace_slug: str = typer.Argument(None, help="Workspace slug (optional, uses current context if omitted)"),
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List members of a workspace."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    # Use current context if no workspace specified
    if not workspace_slug:
        workspace_slug = get_context()
        if not workspace_slug:
            console.print("[red]Error:[/red] No workspace specified and no context set.")
            return
    
    try:
        # First get workspace ID from slug
        response = client.get("/workspaces")
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] Could not load workspaces")
            return
        
        workspaces = response.json()
        workspace = next((ws for ws in workspaces if ws["slug"] == workspace_slug), None)
        
        if not workspace:
            console.print(f"[red]Error:[/red] Workspace '{workspace_slug}' not found")
            return
        
        # Get members
        response = client.get(f"/workspaces/{workspace['id']}/members")
        
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
            columns=["user_id", "role_name", "joined_at"],
            title=f"Members of {workspace['name']}"
        )
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def show_workspace(workspace_identifier: str, output: Optional[OutputFormat] = None):
    """Show workspace details by name or ID."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get(f"/workspaces/{workspace_identifier}")
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        workspace = response.json()
        
        from src.utils import current_output_format, print_output
        
        # For structured formats, output full data
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(workspace)
        else:
            # For text/table, show as single-row table with name first
            print_output(
                workspace,
                columns=["name", "id", "owner_id"]
            )
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
