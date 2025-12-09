"""
Workflow management commands - list, create, get, update, delete, run, export, import
"""

import typer
import json
import yaml
import os
from typing import Optional, List
from rich.console import Console
from src.api_client import get_api_client
from src.utils import OutputFormat, set_output_format, print_output, remove_ids_recursive, current_output_format
import httpx

app = typer.Typer()
console = Console()


def _export_workflow_to_yaml(workflow_data: dict, file_path: str):
    """Export workflow data to a YAML file for deployment."""
    export_data = {
        "apiVersion": "aegis.io/v1",
        "kind": "Workflow",
        "metadata": {
            "name": workflow_data["name"],
            "labels": {
                "app": "aegis",
                "type": "workflow"
            }
        },
        "spec": {
            "name": workflow_data["name"],
            "description": workflow_data.get("description", ""),
            "execution_mode": workflow_data.get("execution_mode", "sequential"),
            "steps": workflow_data.get("steps", []),
            "tags": workflow_data.get("tags", []),
            "metadata": workflow_data.get("metadata", {}),
            "status": workflow_data.get("status", "active")
        }
    }
    
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    with open(file_path, "w") as f:
        yaml.dump(export_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _handle_error(response: httpx.Response, action: str = "perform action"):
    """Handle API error responses consistently."""
    if response.status_code == 401:
        console.print("[red]Error:[/red] Not authenticated. Please login first.")
    elif response.status_code == 404:
        try:
            detail = response.json().get("detail", "Resource not found")
        except:
            detail = "Resource not found"
        console.print(f"[red]Error:[/red] {detail}")
    elif response.status_code == 400:
        try:
            detail = response.json().get("detail", response.text)
        except:
            detail = response.text
        console.print(f"[red]Error:[/red] {detail}")
    else:
        try:
            detail = response.json().get("detail", response.text)
        except:
            detail = response.text
        console.print(f"[red]Error {action}:[/red] {detail}")


@app.command(name="list")
def list_workflows(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (active, inactive, draft)"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml, wide")
):
    """List all workflows."""
    if output and output.lower() not in ["wide"]:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    wide_mode = output and output.lower() == "wide"
    client = get_api_client()
    
    try:
        response = client.list_workflows(status=status, tag=tag)
        
        if response.status_code != 200:
            _handle_error(response, "listing workflows")
            return
        
        workflows = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_workflows = []
            for w in workflows:
                clean_workflows.append(remove_ids_recursive({
                    "name": w["name"],
                    "description": w.get("description", ""),
                    "execution_mode": w.get("execution_mode", ""),
                    "status": w.get("status", ""),
                    "steps": w.get("steps", []),
                    "tags": w.get("tags", [])
                }))
            print_output(clean_workflows, title="Workflows")
        else:
            display_workflows = []
            for w in workflows:
                steps = w.get("steps", [])
                steps_count = len(steps)
                tags_str = ", ".join(w.get("tags", [])[:2])
                
                item = {
                    "name": w["name"],
                    "mode": w.get("execution_mode", "")[:10],
                    "status": w.get("status", ""),
                    "steps": str(steps_count)
                }
                if wide_mode:
                    item["description"] = (w.get("description") or "")[:40]
                    item["tags"] = tags_str or "-"
                
                display_workflows.append(item)
            
            columns = ["name", "mode", "status", "steps"]
            if wide_mode:
                columns.extend(["description", "tags"])
            
            print_output(display_workflows, columns=columns, title="Workflows")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="get")
@app.command(name="show")
def show_workflow(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Show workflow details including steps."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.get_workflow(workflow_identifier)
        
        if response.status_code != 200:
            _handle_error(response, "getting workflow")
            return
        
        workflow = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_workflow = remove_ids_recursive({
                "name": workflow["name"],
                "description": workflow.get("description", ""),
                "execution_mode": workflow.get("execution_mode", ""),
                "status": workflow.get("status", ""),
                "steps": workflow.get("steps", []),
                "tags": workflow.get("tags", []),
                "metadata": workflow.get("metadata", {})
            })
            print_output(clean_workflow)
        else:
            console.print(f"\n[bold cyan]Workflow:[/bold cyan] {workflow['name']}")
            console.print(f"[bold]Execution Mode:[/bold] {workflow.get('execution_mode', '-')}")
            console.print(f"[bold]Status:[/bold] {workflow.get('status', '-')}")
            
            if workflow.get("description"):
                console.print(f"[bold]Description:[/bold] {workflow['description']}")
            
            steps = workflow.get("steps", [])
            if steps:
                console.print(f"\n[bold]Steps ({len(steps)}):[/bold]")
                for i, step in enumerate(steps, 1):
                    step_name = step.get("name", f"Step {i}")
                    agent_id = step.get("agent_id", "")[:8] if step.get("agent_id") else "-"
                    condition = step.get("condition", "")
                    
                    console.print(f"  {i}. [cyan]{step_name}[/cyan]")
                    console.print(f"     Agent: {agent_id}")
                    if condition:
                        console.print(f"     Condition: {condition}")
                    if step.get("input_mapping"):
                        console.print(f"     Input mapping: {json.dumps(step['input_mapping'])[:60]}")
            
            tags = workflow.get("tags", [])
            if tags:
                console.print(f"\n[bold]Tags:[/bold] {', '.join(tags)}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def create(
    name: str = typer.Argument(..., help="Workflow name"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Workflow description"),
    execution_mode: str = typer.Option("sequential", "--mode", "-m", help="Execution mode (sequential, parallel, conditional)"),
    steps_file: Optional[str] = typer.Option(None, "--steps-file", "-f", help="JSON file with steps definition"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    status: str = typer.Option("active", "--status", "-s", help="Initial status (active, inactive, draft)")
):
    """Create a new workflow."""
    client = get_api_client()
    
    steps = []
    if steps_file:
        try:
            with open(steps_file, "r") as f:
                steps = json.load(f)
        except Exception as e:
            console.print(f"[red]Error reading steps file:[/red] {e}")
            return
    
    payload = {
        "name": name,
        "execution_mode": execution_mode,
        "steps": steps,
        "status": status
    }
    
    if description:
        payload["description"] = description
    if tags:
        payload["tags"] = [t.strip() for t in tags.split(",")]
    
    try:
        response = client.create_workflow(payload)
        
        if response.status_code == 201:
            workflow = response.json()
            console.print(f"[green]Workflow '{name}' created successfully![/green]")
            console.print(f"ID: {workflow.get('id')}")
            if not steps:
                console.print("[yellow]Note: Workflow has no steps. Use 'aegis workflow add-step' to add steps.[/yellow]")
        else:
            _handle_error(response, "creating workflow")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def update(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description"),
    execution_mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Execution mode"),
    steps_file: Optional[str] = typer.Option(None, "--steps-file", "-f", help="JSON file with steps definition"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated list of tags"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Status (active, inactive, draft)")
):
    """Update an existing workflow."""
    client = get_api_client()
    
    payload = {}
    
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if execution_mode:
        payload["execution_mode"] = execution_mode
    if status:
        payload["status"] = status
    if tags:
        payload["tags"] = [t.strip() for t in tags.split(",")]
    
    if steps_file:
        try:
            with open(steps_file, "r") as f:
                payload["steps"] = json.load(f)
        except Exception as e:
            console.print(f"[red]Error reading steps file:[/red] {e}")
            return
    
    if not payload:
        console.print("[yellow]No updates specified.[/yellow]")
        return
    
    try:
        response = client.update_workflow(workflow_identifier, payload)
        
        if response.status_code == 200:
            console.print(f"[green]Workflow '{workflow_identifier}' updated successfully![/green]")
        else:
            _handle_error(response, "updating workflow")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def delete(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Delete a workflow."""
    client = get_api_client()
    
    if not yes and not typer.confirm(f"Are you sure you want to delete workflow '{workflow_identifier}'?"):
        return
    
    try:
        response = client.delete_workflow(workflow_identifier)
        
        if response.status_code == 204:
            console.print(f"[green]Workflow '{workflow_identifier}' deleted successfully.[/green]")
        else:
            _handle_error(response, "deleting workflow")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def run(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID"),
    message: str = typer.Argument(..., help="Input message for the workflow"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Context variables as JSON"),
    model_override: Optional[str] = typer.Option(None, "--model", "-m", help="Override model for agents"),
    max_turns: Optional[int] = typer.Option(None, "--max-turns", help="Maximum turns per agent"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion and show result"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Execute a workflow with the given input."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    # Parse context if provided
    context_vars = None
    if context:
        try:
            context_vars = json.loads(context)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing context JSON:[/red] {e}")
            return
    
    try:
        response = client.run_workflow(
            workflow_identifier,
            message,
            context_variables=context_vars,
            model_override=model_override,
            max_turns=max_turns
        )
        
        if response.status_code == 201:
            run_data = response.json()
            run_id = run_data.get("id")
            console.print(f"[green]Workflow run started![/green]")
            console.print(f"Run ID: {run_id}")
            console.print(f"Status: {run_data.get('status')}")
            
            if wait:
                console.print("\n[yellow]Waiting for completion...[/yellow]")
                import time
                while True:
                    time.sleep(2)
                    status_response = client.get_run(run_id)
                    if status_response.status_code == 200:
                        run_status = status_response.json()
                        current_status = run_status.get("status")
                        
                        # Show step progress
                        step_results = run_status.get("step_results", [])
                        if step_results:
                            console.print(f"  Steps completed: {len(step_results)}")
                        
                        if current_status in ["completed", "failed", "cancelled"]:
                            console.print(f"\n[bold]Final Status:[/bold] {current_status}")
                            if run_status.get("output"):
                                console.print(f"[bold]Output:[/bold]\n{run_status['output']}")
                            if run_status.get("error"):
                                console.print(f"[red]Error:[/red] {run_status['error']}")
                            
                            # Show step results
                            if step_results:
                                console.print(f"\n[bold]Step Results:[/bold]")
                                for i, sr in enumerate(step_results, 1):
                                    console.print(f"  {i}. {sr.get('step_name', 'Unknown')}: {sr.get('status', '-')}")
                            break
                    else:
                        console.print("[red]Error checking status[/red]")
                        break
        else:
            _handle_error(response, "running workflow")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def runs(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of runs to show"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """List runs for a specific workflow."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.list_workflow_runs(workflow_identifier, status=status, limit=limit)
        
        if response.status_code != 200:
            _handle_error(response, "listing runs")
            return
        
        runs_data = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(runs_data, title="Workflow Runs")
        else:
            display_runs = []
            for r in runs_data:
                display_runs.append({
                    "id": str(r.get("id", ""))[:8],
                    "status": r.get("status", ""),
                    "started_at": str(r.get("started_at") or "-")[:19],
                    "completed_at": str(r.get("completed_at") or "-")[:19]
                })
            
            print_output(display_runs, columns=["id", "status", "started_at", "completed_at"],
                        title=f"Runs for Workflow: {workflow_identifier}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="add-step")
def add_step(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID"),
    step_name: str = typer.Option(..., "--name", "-n", help="Step name"),
    agent_id: str = typer.Option(..., "--agent", "-a", help="Agent ID for this step"),
    condition: Optional[str] = typer.Option(None, "--condition", "-c", help="Condition for step execution"),
    input_mapping: Optional[str] = typer.Option(None, "--input-mapping", "-i", help="Input mapping as JSON")
):
    """Add a step to a workflow."""
    client = get_api_client()
    
    try:
        # Get current workflow
        response = client.get_workflow(workflow_identifier)
        if response.status_code != 200:
            _handle_error(response, "getting workflow")
            return
        
        workflow = response.json()
        steps = workflow.get("steps", [])
        
        # Create new step
        new_step = {
            "name": step_name,
            "agent_id": agent_id
        }
        if condition:
            new_step["condition"] = condition
        if input_mapping:
            try:
                new_step["input_mapping"] = json.loads(input_mapping)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error parsing input mapping JSON:[/red] {e}")
                return
        
        steps.append(new_step)
        
        # Update workflow
        update_response = client.update_workflow(workflow_identifier, {"steps": steps})
        
        if update_response.status_code == 200:
            console.print(f"[green]Step '{step_name}' added to workflow '{workflow_identifier}'[/green]")
            console.print(f"Total steps: {len(steps)}")
        else:
            _handle_error(update_response, "updating workflow")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="remove-step")
def remove_step(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID"),
    step_name: str = typer.Argument(..., help="Step name to remove"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Remove a step from a workflow."""
    client = get_api_client()
    
    if not yes and not typer.confirm(f"Remove step '{step_name}' from workflow?"):
        return
    
    try:
        # Get current workflow
        response = client.get_workflow(workflow_identifier)
        if response.status_code != 200:
            _handle_error(response, "getting workflow")
            return
        
        workflow = response.json()
        steps = workflow.get("steps", [])
        
        # Find and remove step
        original_count = len(steps)
        steps = [s for s in steps if s.get("name") != step_name]
        
        if len(steps) == original_count:
            console.print(f"[yellow]Step '{step_name}' not found in workflow[/yellow]")
            return
        
        # Update workflow
        update_response = client.update_workflow(workflow_identifier, {"steps": steps})
        
        if update_response.status_code == 200:
            console.print(f"[green]Step '{step_name}' removed from workflow[/green]")
            console.print(f"Remaining steps: {len(steps)}")
        else:
            _handle_error(update_response, "updating workflow")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="clone")
def clone_workflow(
    workflow_identifier: str = typer.Argument(..., help="Workflow to clone"),
    new_name: str = typer.Argument(..., help="Name for the cloned workflow")
):
    """Clone an existing workflow with a new name."""
    client = get_api_client()
    
    try:
        # Get source workflow
        response = client.get_workflow(workflow_identifier)
        if response.status_code != 200:
            _handle_error(response, "getting source workflow")
            return
        
        source = response.json()
        
        # Create new workflow with same config
        payload = {
            "name": new_name,
            "description": f"Clone of {source['name']}. " + (source.get("description") or ""),
            "execution_mode": source.get("execution_mode", "sequential"),
            "steps": source.get("steps", []),
            "tags": source.get("tags", []),
            "metadata": source.get("metadata", {}),
            "status": "draft"  # Start cloned workflow as draft
        }
        
        create_response = client.create_workflow(payload)
        if create_response.status_code == 201:
            new_workflow = create_response.json()
            console.print(f"[green]Workflow cloned successfully![/green]")
            console.print(f"New workflow: {new_name}")
            console.print(f"ID: {new_workflow.get('id')}")
        else:
            _handle_error(create_response, "creating cloned workflow")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="export")
def export_workflow(
    workflow_identifier: str = typer.Argument(..., help="Workflow name or ID to export"),
    output_file: str = typer.Option(None, "--output", "-o", help="Output YAML file path"),
    include_all: bool = typer.Option(False, "--all", "-a", help="Export all workflows")
):
    """Export workflow(s) to YAML file(s) for deployment/backup."""
    client = get_api_client()
    
    try:
        if include_all:
            response = client.list_workflows()
            if response.status_code != 200:
                _handle_error(response, "listing workflows")
                return
            
            workflows = response.json()
            output_dir = output_file or "workflows"
            os.makedirs(output_dir, exist_ok=True)
            
            for wf in workflows:
                file_path = os.path.join(output_dir, f"{wf['name']}.yaml")
                _export_workflow_to_yaml(wf, file_path)
                console.print(f"[green]Exported:[/green] {wf['name']} -> {file_path}")
            
            console.print(f"\n[green]Exported {len(workflows)} workflows to {output_dir}/[/green]")
        else:
            response = client.get_workflow(workflow_identifier)
            if response.status_code != 200:
                _handle_error(response, "getting workflow")
                return
            
            wf = response.json()
            file_path = output_file or f"{wf['name']}.yaml"
            _export_workflow_to_yaml(wf, file_path)
            console.print(f"[green]Workflow '{wf['name']}' exported to: {file_path}[/green]")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="import")
def import_workflow(
    file_path: str = typer.Argument(..., help="YAML file to import"),
    update_existing: bool = typer.Option(False, "--update", "-u", help="Update if workflow exists")
):
    """Import workflow from YAML file."""
    client = get_api_client()
    
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        
        if "spec" in data:
            workflow_data = data["spec"]
        else:
            workflow_data = data
        
        payload = {
            "name": workflow_data["name"],
            "description": workflow_data.get("description"),
            "execution_mode": workflow_data.get("execution_mode", "sequential"),
            "steps": workflow_data.get("steps", []),
            "tags": workflow_data.get("tags", []),
            "metadata": workflow_data.get("metadata", {}),
            "status": workflow_data.get("status", "active")
        }
        
        existing_response = client.list_workflows()
        existing_names = []
        if existing_response.status_code == 200:
            existing_names = [w["name"] for w in existing_response.json()]
        
        if payload["name"] in existing_names:
            if update_existing:
                existing = next((w for w in existing_response.json() if w["name"] == payload["name"]), None)
                if existing:
                    response = client.update_workflow(str(existing["id"]), payload)
                    if response.status_code == 200:
                        console.print(f"[green]Workflow '{payload['name']}' updated from {file_path}[/green]")
                    else:
                        _handle_error(response, "updating workflow")
            else:
                console.print(f"[yellow]Workflow '{payload['name']}' already exists. Use --update to overwrite.[/yellow]")
        else:
            response = client.create_workflow(payload)
            if response.status_code == 201:
                wf = response.json()
                console.print(f"[green]Workflow '{payload['name']}' imported successfully![/green]")
                console.print(f"ID: {wf.get('id')}")
            else:
                _handle_error(response, "creating workflow")
                
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] File not found: {file_path}")
    except yaml.YAMLError as e:
        console.print(f"[red]Error parsing YAML:[/red] {e}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
