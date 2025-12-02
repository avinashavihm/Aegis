import typer
from typing import Optional, List
from rich.console import Console
from rich.syntax import Syntax
import json
from src.api_client import get_api_client
from src.utils import print_output, OutputFormat, set_output_format
from src.config import get_context
import httpx
import uuid

app = typer.Typer()
console = Console()

def list_roles(
    team: bool = typer.Option(False, "--team", "-t", help="List roles for current team context"),
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List roles."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    params = {}
    if team:
        current_context = get_context()
        if not current_context:
            console.print("[red]Error:[/red] No team context set. Use 'aegis team set <name>' or omit --team.")
            return
            
        try:
            response = client.get("/teams")
            if response.status_code == 200:
                teams = response.json()
                t = next((t for t in teams if t["name"] == current_context), None)
                if t:
                    params["team_id"] = t["id"]
                else:
                    console.print(f"[red]Error:[/red] Team '{current_context}' not found.")
                    return
        except Exception as e:
            console.print(f"[red]Error resolving team:[/red] {e}")
            return

    try:
        response = client.get("/roles", params=params)
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        roles = response.json()
        
        from src.utils import current_output_format
        
        # For structured formats (JSON/YAML), remove IDs and timestamps
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_roles = []
            for r in roles:
                clean_r = {
                    "name": r["name"],
                    "scope": "Team" if r["team_id"] else "Global",
                    "description": r.get("description", ""),
                    "policies": [p.get('name', p.get('policy_name', '')) for p in r.get("policies", [])]
                }
                clean_roles.append(clean_r)
            print_output(clean_roles)
        else:
            # For table/text, show summary
            display_roles = []
            for r in roles:
                display_roles.append({
                    "name": r["name"],
                    "scope": "Team" if r["team_id"] else "Global",
                    "description": r["description"] or "",
                    "id": r["id"]
                })
                
            print_output(
                display_roles,
                columns=["name", "scope", "description"],
                title="Roles"
            )

    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error listing roles:[/red] {e}")


@app.command()
def create(
    name: str,
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Role description"),
    policy_ids: Optional[List[str]] = typer.Option(None, "--policy", "-p", help="Policy IDs or Names to attach"),
    team: bool = typer.Option(False, "--team", "-t", help="Create as team-specific role (uses current context)")
):
    """Create a new role."""
    client = get_api_client()
    
    # Resolve policy IDs if names provided
    resolved_policy_ids = []
    if policy_ids:
        try:
            response = client.get("/policies")
            if response.status_code == 200:
                all_policies = response.json()
                for pid in policy_ids:
                    # Check if UUID
                    try:
                        uuid.UUID(pid)
                        resolved_policy_ids.append(pid)
                    except ValueError:
                        # Find by name
                        p = next((p for p in all_policies if p["name"] == pid), None)
                        if p:
                            resolved_policy_ids.append(p["id"])
                        else:
                            console.print(f"[yellow]Warning:[/yellow] Policy '{pid}' not found, skipping.")
        except Exception as e:
            console.print(f"[red]Error resolving policies:[/red] {e}")
            return

    payload = {
        "name": name,
        "description": description,
        "policy_ids": resolved_policy_ids
    }
    
    if team:
        current_context = get_context()
        if not current_context:
            console.print("[red]Error:[/red] No team context set. Use 'aegis team set <name>'")
            return
            
        try:
            response = client.get("/teams")
            if response.status_code == 200:
                teams = response.json()
                t = next((t for t in teams if t["name"] == current_context), None)
                if t:
                    payload["team_id"] = t["id"]
                else:
                    console.print(f"[red]Error:[/red] Team '{current_context}' not found.")
                    return
        except Exception:
            pass 

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
    """Show role details including policies."""
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
                "scope": "Team" if role["team_id"] else "Global",
                "description": role["description"] or ""
            }
            print_output(
                display_role,
                columns=["name", "id", "scope", "description"]
            )
            
            # Show attached policies
            if "policies" in role and role["policies"]:
                console.print("\n[bold]Attached Policies:[/bold]")
                print_output(
                    role["policies"],
                    columns=["name", "description"],
                    title=None
                )
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")



@app.command(name="edit")
@app.command(name="update", hidden=True)
def update(
    role_identifier: str = typer.Argument(..., help="Role name or ID"),
    name: str = typer.Option(None, "--name", "-n", help="New name"),
    description: str = typer.Option(None, "--desc", "-d", help="New description"),
    policy_ids: List[str] = typer.Option(None, "--policy", "-p", help="Policy IDs or Names to attach (replaces existing)")
):
    """Update a role."""
    client = get_api_client()
    
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    
    # Resolve policy IDs if provided
    if policy_ids is not None:
        resolved_policy_ids = []
        try:
            response = client.get("/policies")
            if response.status_code == 200:
                all_policies = response.json()
                for pid in policy_ids:
                    # Check if UUID
                    try:
                        uuid.UUID(pid)
                        resolved_policy_ids.append(pid)
                    except ValueError:
                        # Find by name
                        p = next((p for p in all_policies if p["name"] == pid), None)
                        if p:
                            resolved_policy_ids.append(p["id"])
                        else:
                            console.print(f"[yellow]Warning:[/yellow] Policy '{pid}' not found, skipping.")
        except Exception as e:
            console.print(f"[red]Error resolving policies:[/red] {e}")
            return
        payload["policy_ids"] = resolved_policy_ids
            
    if not payload:
        console.print("[yellow]No updates provided.[/yellow]")
        return

    try:
        response = client.put(f"/roles/{role_identifier}", json=payload)
        
        if response.status_code == 200:
            role = response.json()
            console.print(f"[green]Role updated successfully![/green]")
            console.print(f"ID: {role['id']}")
            console.print(f"Name: {role['name']}")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] Role '{role_identifier}' not found")
        else:
            console.print(f"[red]Error updating role:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def delete(role_identifier: str):
    """Delete a role."""
    client = get_api_client()
    
    if not typer.confirm(f"Are you sure you want to delete role {role_identifier}?"):
        return

    try:
        response = client.delete(f"/roles/{role_identifier}")
        
        if response.status_code == 204:
            console.print("[green]Role deleted successfully.[/green]")
        else:
            console.print(f"[red]Error deleting role:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def attach_policy(role_identifier: str, policy_identifier: str):
    """Attach a policy to a role (internal function called by main command)."""
    client = get_api_client()
    
    try:
        response = client.post(f"/roles/{role_identifier}/policies/{policy_identifier}", json={})
        
        if response.status_code == 200:
            console.print(f"[green]Policy '{policy_identifier}' attached to role '{role_identifier}'.[/green]")
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

