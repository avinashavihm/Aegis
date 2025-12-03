import typer
from typing import Optional
from rich.console import Console
from src.api_client import get_api_client
from src.utils import OutputFormat, set_output_format, print_output
import httpx

app = typer.Typer()
console = Console()


@app.command()
def create(
    name: str,
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Workspace description")
):
    """Create a new workspace."""
    client = get_api_client()
    
    payload = {"name": name}
    if description:
        payload["description"] = description
    
    try:
        response = client.post("/workspaces", json=payload)
        
        if response.status_code == 201:
            workspace = response.json()
            console.print(f"[green]Workspace '{name}' created successfully![/green]")
        elif response.status_code == 400:
            console.print(f"[red]Error:[/red] {response.json().get('detail', response.text)}")
        elif response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
        elif response.status_code == 409:
            console.print(f"[red]Error:[/red] Workspace '{name}' already exists")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error creating workspace:[/red] {e}")


@app.command(name="list")
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
        
        from src.utils import current_output_format
        
        # For structured formats, remove IDs
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_workspaces = []
            for ws in workspaces:
                clean_ws = {
                    "name": ws["name"],
                    "description": ws.get("description", ""),
                    "owner": ws.get("owner_username", ""),
                    "content": ws.get("content", {})
                }
                clean_workspaces.append(clean_ws)
            print_output(clean_workspaces, title="Workspaces")
        else:
            # Format for table display
            display_workspaces = []
            for ws in workspaces:
                display_workspaces.append({
                    "name": ws["name"],
                    "description": (ws.get("description") or "")[:50] or "-",
                    "owner": ws.get("owner_username", "")
                })
            
            print_output(
                display_workspaces,
                columns=["name", "description", "owner"],
                title="Workspaces"
            )
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error listing workspaces:[/red] {e}")


@app.command(name="show")
@app.command(name="get")
def show_workspace(
    workspace_identifier: str,
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
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
        
        from src.utils import current_output_format
        
        # For structured formats, remove IDs
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_workspace = {
                "name": workspace["name"],
                "description": workspace.get("description", ""),
                "owner": workspace.get("owner_username", ""),
                "content": workspace.get("content", {})
            }
            print_output(clean_workspace)
        else:
            # Show as single-row table
            print_output(
                workspace,
                columns=["name", "description", "owner_username"]
            )
            
            # Show content separately
            if "content" in workspace and workspace.get("content"):
                console.print("\n[bold]Content (Agents & Workflows):[/bold]")
                console.print_json(data=workspace["content"])
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def delete(
    workspace_identifier: str,
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Delete a workspace."""
    client = get_api_client()
    
    if not yes and not typer.confirm(f"Are you sure you want to delete workspace {workspace_identifier}?"):
        return
    
    try:
        response = client.delete(f"/workspaces/{workspace_identifier}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                message = result.get('message', 'Workspace deleted successfully')
                console.print(f"[green]{message}[/green]")
            except:
                console.print(f"[green]Workspace '{workspace_identifier}' deleted successfully.[/green]")
        elif response.status_code == 404:
            try:
                error_detail = response.json().get('detail', response.text)
                console.print(f"[red]Error:[/red] {error_detail}")
            except:
                console.print(f"[red]Error:[/red] Workspace '{workspace_identifier}' not found")
        else:
            try:
                error_detail = response.json().get('detail', response.text)
                console.print(f"[red]Error deleting workspace:[/red] {error_detail}")
            except:
                console.print(f"[red]Error deleting workspace:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")



