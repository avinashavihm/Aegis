import typer
from typing import Optional
from rich.console import Console
from rich.syntax import Syntax
import json
from src.api_client import get_api_client
from src.utils import print_output, OutputFormat, set_output_format
from src.config import get_context
import httpx

app = typer.Typer()
console = Console()

@app.command(name="list")
@app.command(name="ls")
def list_roles(
    workspace: bool = typer.Option(False, "--workspace", "-w", help="List roles for current workspace context"),
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List roles."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    params = {}
    if workspace:
        current_context = get_context()
        if not current_context:
            console.print("[red]Error:[/red] No workspace context set. Use 'aegis workspace set <slug>' or omit --workspace.")
            return
            
        # We need workspace ID, but context stores slug. 
        # Ideally we should store ID in config or fetch it.
        # For now, let's fetch workspace by slug to get ID.
        # This is a bit inefficient but works.
        try:
            # List workspaces to find the one with matching slug
            # Or better, if we had a get-by-slug endpoint.
            # Let's assume we can filter list by slug or just iterate.
            response = client.get("/workspaces")
            if response.status_code == 200:
                workspaces = response.json()
                ws = next((w for w in workspaces if w["slug"] == current_context), None)
                if ws:
                    params["workspace_id"] = ws["id"]
                else:
                    console.print(f"[red]Error:[/red] Workspace '{current_context}' not found.")
                    return
        except Exception as e:
            console.print(f"[red]Error resolving workspace:[/red] {e}")
            return

    try:
        response = client.get("/roles", params=params)
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        roles = response.json()
        
        from src.utils import current_output_format
        
        # For structured formats (JSON/YAML), show full role data including policy
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(roles)
        else:
            # For table/text, show summary
            display_roles = []
            for r in roles:
                display_roles.append({
                    "name": r["name"],
                    "id": r["id"],
                    "scope": "Workspace" if r["workspace_id"] else "Global",
                    "description": r["description"] or ""
                })
                
            print_output(
                display_roles,
                columns=["name", "id", "scope", "description"],
                title="Roles"
            )

    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error listing roles:[/red] {e}")


@app.command()
def create(
    name: str,
    description: str = typer.Option(None, "--desc", "-d", help="Role description"),
    policy_file: str = typer.Option(..., "--policy", "-p", help="Path to JSON policy file"),
    workspace: bool = typer.Option(False, "--workspace", "-w", help="Create as workspace-specific role (uses current context)")
):
    """Create a new role."""
    client = get_api_client()
    
    # Load policy
    try:
        with open(policy_file, "r") as f:
            policy = json.load(f)
    except Exception as e:
        console.print(f"[red]Error reading policy file:[/red] {e}")
        return

    payload = {
        "name": name,
        "description": description,
        "policy": policy
    }
    
    if workspace:
        current_context = get_context()
        if not current_context:
            console.print("[red]Error:[/red] No workspace context set. Use 'aegis workspace set <slug>'")
            return
            
        # Resolve workspace ID (same logic as list)
        try:
            response = client.get("/workspaces")
            if response.status_code == 200:
                workspaces = response.json()
                ws = next((w for w in workspaces if w["slug"] == current_context), None)
                if ws:
                    payload["workspace_id"] = ws["id"]
                else:
                    console.print(f"[red]Error:[/red] Workspace '{current_context}' not found.")
                    return
        except Exception:
            pass # API error handled below

    try:
        response = client.post("/roles", json=payload)
        
        if response.status_code == 201:
            role = response.json()
            console.print(f"[green]Role created successfully![/green] ID: {role['id']}")
        else:
            console.print(f"[red]Error creating role:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="show")
@app.command(name="get")
def show_role(
    role_identifier: str = typer.Argument(..., help="Role name or ID"),
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """Show role details including policy."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get(f"/roles/{role_identifier}")
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        role = response.json()
        
        from src.utils import current_output_format
        
        # For structured formats, output the role data directly
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(role)
        else:
            # For text/table, show as a single-row table
            display_role = {
                "name": role["name"],
                "id": role["id"],
                "scope": "Workspace" if role["workspace_id"] else "Global",
                "description": role["description"] or ""
            }
            print_output(
                display_role,
                columns=["name", "id", "scope", "description"]
            )

    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def delete(role_id: str):
    """Delete a role."""
    client = get_api_client()
    
    if not typer.confirm(f"Are you sure you want to delete role {role_id}?"):
        return

    try:
        response = client.delete(f"/roles/{role_id}")
        
        if response.status_code == 204:
            console.print("[green]Role deleted successfully.[/green]")
        else:
            console.print(f"[red]Error deleting role:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
