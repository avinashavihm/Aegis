import typer
from typing import Optional
from rich.console import Console
from src.api_client import get_api_client
from src.utils import OutputFormat, set_output_format
import httpx
import json

app = typer.Typer()
console = Console()

@app.command()
def create(
    name: str,
    content: str = typer.Option(..., "--content", "-c", help="Policy content (JSON string)"),
    description: str = typer.Option(None, "--desc", "-d", help="Policy description")
):
    """Create a new policy."""
    client = get_api_client()
    
    try:
        # Validate JSON
        try:
            json_content = json.loads(content)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Invalid JSON content")
            return

        response = client.post("/policies", json={
            "name": name,
            "description": description,
            "content": json_content
        })
        
        if response.status_code == 201:
            policy = response.json()
            console.print(f"[green]Policy created successfully![/green]")
        elif response.status_code == 400:
            console.print(f"[red]Error:[/red] {response.json()['detail']}")
        elif response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error creating policy:[/red] {e}")

def list_policies(
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List all policies."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get("/policies")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        policies = response.json()
        
        from src.utils import print_output, current_output_format
        
        # For structured formats (JSON/YAML), remove IDs and timestamps
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_policies = []
            for p in policies:
                clean_p = {
                    "name": p["name"],
                    "description": p.get("description", ""),
                    "content": p.get("content", {})
                }
                clean_policies.append(clean_p)
            print_output(clean_policies, title="Policies")
        else:
            print_output(
                policies,
                columns=["name", "description"],
                title="Policies"
            )
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error listing policies:[/red] {e}")

def show_policy(policy_identifier: str, output: Optional[OutputFormat] = None):
    """Show policy details by name or ID."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get(f"/policies/{policy_identifier}")
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        policy = response.json()
        
        from src.utils import current_output_format, print_output
        
        # For structured formats, output full data including content
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(policy)
        else:
            # For text/table, show summary
            print_output(
                policy,
                columns=["name", "id", "description"]
            )
            # Show content separately
            console.print("\n[bold]Content:[/bold]")
            console.print_json(data=policy["content"])
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def update(
    policy_identifier: str = typer.Argument(..., help="Policy name or ID"),
    name: str = typer.Option(None, "--name", "-n", help="New name"),
    description: str = typer.Option(None, "--desc", "-d", help="New description"),
    content: str = typer.Option(None, "--content", "-c", help="New content (JSON string)")
):
    """Update a policy."""
    client = get_api_client()
    
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if content:
        try:
            payload["content"] = json.loads(content)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Invalid JSON content")
            return
            
    if not payload:
        console.print("[yellow]No updates provided.[/yellow]")
        return

    try:
        response = client.put(f"/policies/{policy_identifier}", json=payload)
        
        if response.status_code == 200:
            policy = response.json()
            console.print(f"[green]Policy updated successfully![/green]")
            console.print(f"Name: {policy['name']}")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Policy '{policy_identifier}' not found")
        else:
            console.print(f"[red]Error updating policy:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def delete(policy_identifier: str):
    """Delete a policy."""
    client = get_api_client()
    
    if not typer.confirm(f"Are you sure you want to delete policy {policy_identifier}?"):
        return

    try:
        response = client.delete(f"/policies/{policy_identifier}")
        
        if response.status_code == 204:
            console.print("[green]Policy deleted successfully.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Policy '{policy_identifier}' not found")
        else:
            console.print(f"[red]Error deleting policy:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
