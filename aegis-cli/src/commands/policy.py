import typer
from typing import Optional, List
from rich.console import Console
from src.api_client import get_api_client
from src.utils import OutputFormat, set_output_format
import httpx
import json
import yaml
from pathlib import Path

app = typer.Typer()
console = Console()

@app.command()
def create(
    name: str,
    content: Optional[str] = typer.Option(None, "--content", "-c", help="Policy content (JSON string)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to JSON file containing policy content"),
    description: str = typer.Option(None, "--desc", "-d", help="Policy description")
):
    """Create a new policy from JSON content or file."""
    client = get_api_client()
    
    # Validate that either content or file is provided
    if not content and not file:
        console.print("[red]Error:[/red] Either --content or --file must be provided")
        return
    
    if content and file:
        console.print("[red]Error:[/red] Cannot specify both --content and --file")
        return
    
    try:
        # Read content from file or use provided content
        if file:
            file_path = Path(file)
            if not file_path.exists():
                console.print(f"[red]Error:[/red] File not found: {file}")
                return
            
            try:
                with open(file_path, 'r') as f:
                    file_content = f.read()
                
                # Check if file contains multiple YAML documents (separated by ---)
                if '---' in file_content:
                    # Parse multiple YAML documents
                    policies_data = []
                    for doc in yaml.safe_load_all(file_content):
                        if doc:
                            policies_data.append(doc)
                    
                    if not policies_data:
                        console.print("[red]Error:[/red] No valid policies found in file")
                        return
                    
                    # Create multiple policies
                    created_count = 0
                    failed_count = 0
                    
                    for policy_data in policies_data:
                        policy_name = policy_data.get('name') or name
                        policy_desc = policy_data.get('description') or description
                        policy_content = policy_data.get('content') or policy_data
                        
                        # If content is a dict without 'content' key, use the whole dict
                        if 'content' not in policy_data and isinstance(policy_data, dict):
                            # Remove metadata keys
                            policy_content = {k: v for k, v in policy_data.items() 
                                            if k not in ['name', 'description']}
                        
                        response = client.post("/policies", json={
                            "name": policy_name,
                            "description": policy_desc,
                            "content": policy_content
                        })
                        
                        if response.status_code == 201:
                            created_count += 1
                            console.print(f"[green]Policy '{policy_name}' created successfully![/green]")
                        else:
                            failed_count += 1
                            error_msg = response.json().get('detail', response.text) if response.status_code == 400 else response.text
                            console.print(f"[red]Error creating policy '{policy_name}':[/red] {error_msg}")
                    
                    console.print(f"\n[bold]Summary:[/bold] {created_count} created, {failed_count} failed")
                    return
                else:
                    # Try to parse as JSON first
                    try:
                        json_content = json.loads(file_content)
                    except json.JSONDecodeError:
                        # Try YAML
                        try:
                            yaml_content = yaml.safe_load(file_content)
                            if isinstance(yaml_content, dict):
                                # If it has 'content' key, use that, otherwise use whole dict
                                json_content = yaml_content.get('content', yaml_content)
                            else:
                                json_content = yaml_content
                        except yaml.YAMLError as e:
                            console.print(f"[red]Error:[/red] Invalid JSON or YAML in file: {e}")
                            return
            except Exception as e:
                console.print(f"[red]Error:[/red] Failed to read file: {e}")
                return
        else:
            # Validate JSON from content string
            try:
                json_content = json.loads(content)
            except json.JSONDecodeError:
                console.print("[red]Error:[/red] Invalid JSON content")
                return

        # Create single policy
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
    content: Optional[str] = typer.Option(None, "--content", "-c", help="New content (JSON string)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to JSON file containing new policy content")
):
    """Update a policy."""
    client = get_api_client()
    
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if content and file:
        console.print("[red]Error:[/red] Cannot specify both --content and --file")
        return
    if content:
        try:
            payload["content"] = json.loads(content)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Invalid JSON content")
            return
    elif file:
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[red]Error:[/red] File not found: {file}")
            return
        try:
            with open(file_path, 'r') as f:
                payload["content"] = json.load(f)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] Invalid JSON in file: {e}")
            return
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to read file: {e}")
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
