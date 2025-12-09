"""
Run management commands - list, get, cancel, delete runs and show stats
"""

import typer
import json
from typing import Optional
from rich.console import Console
from src.api_client import get_api_client
from src.utils import OutputFormat, set_output_format, print_output, remove_ids_recursive, current_output_format
import httpx

app = typer.Typer()
console = Console()


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
def list_runs(
    run_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type (agent, workflow)"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending, running, completed, failed, cancelled)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Number of runs to show"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml, wide")
):
    """List all runs."""
    if output and output.lower() not in ["wide"]:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    wide_mode = output and output.lower() == "wide"
    client = get_api_client()
    
    try:
        response = client.list_runs(run_type=run_type, status=status, limit=limit)
        
        if response.status_code != 200:
            _handle_error(response, "listing runs")
            return
        
        runs = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(runs, title="Runs")
        else:
            display_runs = []
            for r in runs:
                item = {
                    "id": str(r.get("id", ""))[:8],
                    "type": r.get("run_type", ""),
                    "status": r.get("status", ""),
                    "started": str(r.get("started_at") or "-")[:19]
                }
                if wide_mode:
                    item["completed"] = str(r.get("completed_at") or "-")[:19]
                    item["agent_id"] = str(r.get("agent_id") or "-")[:8]
                    item["workflow_id"] = str(r.get("workflow_id") or "-")[:8]
                display_runs.append(item)
            
            columns = ["id", "type", "status", "started"]
            if wide_mode:
                columns.extend(["completed", "agent_id", "workflow_id"])
            
            print_output(display_runs, columns=columns, title="Runs")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="get")
@app.command(name="show")
def show_run(
    run_id: str = typer.Argument(..., help="Run ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Show run details."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.get_run(run_id)
        
        if response.status_code != 200:
            _handle_error(response, "getting run")
            return
        
        run_data = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(run_data)
        else:
            console.print(f"\n[bold cyan]Run:[/bold cyan] {run_data.get('id', '')[:8]}...")
            console.print(f"[bold]Type:[/bold] {run_data.get('run_type', '-')}")
            console.print(f"[bold]Status:[/bold] {run_data.get('status', '-')}")
            
            if run_data.get("agent_id"):
                console.print(f"[bold]Agent ID:[/bold] {run_data['agent_id']}")
            if run_data.get("workflow_id"):
                console.print(f"[bold]Workflow ID:[/bold] {run_data['workflow_id']}")
            
            console.print(f"[bold]Started:[/bold] {run_data.get('started_at') or '-'}")
            console.print(f"[bold]Completed:[/bold] {run_data.get('completed_at') or '-'}")
            
            if run_data.get("input_message"):
                console.print(f"\n[bold]Input:[/bold]")
                console.print(run_data["input_message"][:500])
                if len(run_data.get("input_message", "")) > 500:
                    console.print("... (truncated)")
            
            if run_data.get("output"):
                console.print(f"\n[bold]Output:[/bold]")
                console.print(run_data["output"][:1000])
                if len(run_data.get("output", "")) > 1000:
                    console.print("... (truncated)")
            
            if run_data.get("error"):
                console.print(f"\n[bold red]Error:[/bold red] {run_data['error']}")
            
            # Show step results for workflows
            step_results = run_data.get("step_results", [])
            if step_results:
                console.print(f"\n[bold]Step Results ({len(step_results)}):[/bold]")
                for i, sr in enumerate(step_results, 1):
                    console.print(f"  {i}. {sr.get('step_name', 'Unknown')}: {sr.get('status', '-')}")
            
            # Show tool calls
            tool_calls = run_data.get("tool_calls", [])
            if tool_calls:
                console.print(f"\n[bold]Tool Calls ({len(tool_calls)}):[/bold]")
                for tc in tool_calls[:10]:
                    console.print(f"  • {tc.get('name', 'Unknown')}")
                if len(tool_calls) > 10:
                    console.print(f"  ... and {len(tool_calls) - 10} more")
            
            # Show token usage
            tokens = run_data.get("tokens_used", 0)
            if tokens:
                console.print(f"\n[bold]Tokens Used:[/bold] {tokens}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def cancel(
    run_id: str = typer.Argument(..., help="Run ID to cancel"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Cancel a running execution."""
    client = get_api_client()
    
    if not yes and not typer.confirm(f"Are you sure you want to cancel run '{run_id[:8]}...'?"):
        return
    
    try:
        response = client.cancel_run(run_id)
        
        if response.status_code == 200:
            run_data = response.json()
            console.print(f"[green]Run cancelled successfully.[/green]")
            console.print(f"Status: {run_data.get('status')}")
        else:
            _handle_error(response, "cancelling run")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def delete(
    run_id: str = typer.Argument(..., help="Run ID to delete"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Delete a run record."""
    client = get_api_client()
    
    if not yes and not typer.confirm(f"Are you sure you want to delete run '{run_id[:8]}...'?"):
        return
    
    try:
        response = client.delete_run(run_id)
        
        if response.status_code == 204:
            console.print(f"[green]Run deleted successfully.[/green]")
        else:
            _handle_error(response, "deleting run")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def watch(
    run_id: str = typer.Argument(..., help="Run ID to watch"),
    interval: int = typer.Option(2, "--interval", "-i", help="Poll interval in seconds")
):
    """Watch a run until completion."""
    import time
    
    client = get_api_client()
    
    try:
        console.print(f"[yellow]Watching run {run_id[:8]}...[/yellow]")
        console.print("Press Ctrl+C to stop watching\n")
        
        last_status = None
        while True:
            response = client.get_run(run_id)
            
            if response.status_code != 200:
                _handle_error(response, "getting run")
                break
            
            run_data = response.json()
            current_status = run_data.get("status")
            
            if current_status != last_status:
                console.print(f"[{_status_color(current_status)}]Status: {current_status}[/{_status_color(current_status)}]")
                last_status = current_status
            
            if current_status in ["completed", "failed", "cancelled"]:
                console.print(f"\n[bold]Final Status:[/bold] {current_status}")
                
                if run_data.get("output"):
                    console.print(f"\n[bold]Output:[/bold]")
                    console.print(run_data["output"])
                
                if run_data.get("error"):
                    console.print(f"\n[bold red]Error:[/bold red] {run_data['error']}")
                
                tokens = run_data.get("tokens_used", 0)
                if tokens:
                    console.print(f"\n[bold]Tokens Used:[/bold] {tokens}")
                
                break
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching.[/yellow]")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def _status_color(status: str) -> str:
    """Get color for status."""
    colors = {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "failed": "red",
        "cancelled": "magenta"
    }
    return colors.get(status, "white")


@app.command()
def stats(
    days: int = typer.Option(30, "--days", "-d", help="Number of days for statistics"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Show run statistics."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.get_run_stats(days=days)
        
        if response.status_code != 200:
            _handle_error(response, "getting statistics")
            return
        
        stats_data = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(stats_data)
        else:
            console.print(f"\n[bold cyan]Run Statistics (Last {days} days)[/bold cyan]\n")
            
            # Total runs
            total = stats_data.get("total_runs", 0)
            console.print(f"[bold]Total Runs:[/bold] {total}")
            
            # Status breakdown
            by_status = stats_data.get("by_status", {})
            if by_status:
                console.print(f"\n[bold]By Status:[/bold]")
                for status, count in by_status.items():
                    pct = (count / total * 100) if total > 0 else 0
                    console.print(f"  [{_status_color(status)}]{status}[/{_status_color(status)}]: {count} ({pct:.1f}%)")
            
            # Type breakdown
            by_type = stats_data.get("by_type", {})
            if by_type:
                console.print(f"\n[bold]By Type:[/bold]")
                for run_type, count in by_type.items():
                    console.print(f"  {run_type}: {count}")
            
            # Average tokens
            avg_tokens = stats_data.get("avg_tokens_per_run", 0)
            if avg_tokens:
                console.print(f"\n[bold]Average Tokens per Run:[/bold] {avg_tokens:.0f}")
            
            # Success rate
            success_rate = stats_data.get("success_rate", 0)
            console.print(f"[bold]Success Rate:[/bold] {success_rate:.1f}%")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def logs(
    run_id: str = typer.Argument(..., help="Run ID"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow logs in real-time"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show")
):
    """Show logs for a run (messages and tool calls)."""
    import time
    
    client = get_api_client()
    
    try:
        response = client.get_run(run_id)
        
        if response.status_code != 200:
            _handle_error(response, "getting run")
            return
        
        run_data = response.json()
        
        # Show messages
        messages = run_data.get("messages", [])
        if messages:
            console.print(f"[bold]Messages ({len(messages)}):[/bold]\n")
            for msg in messages[-tail:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                
                if role == "user":
                    console.print(f"[cyan]User:[/cyan] {content}")
                elif role == "assistant":
                    console.print(f"[green]Assistant:[/green] {content}")
                elif role == "system":
                    console.print(f"[yellow]System:[/yellow] {content}")
                elif role == "tool":
                    console.print(f"[magenta]Tool:[/magenta] {content}")
                else:
                    console.print(f"[dim]{role}:[/dim] {content}")
                
                if len(msg.get("content", "")) > 200:
                    console.print("  ... (truncated)")
        
        # Show tool calls
        tool_calls = run_data.get("tool_calls", [])
        if tool_calls:
            console.print(f"\n[bold]Tool Calls ({len(tool_calls)}):[/bold]\n")
            for tc in tool_calls[-tail:]:
                name = tc.get("name", "Unknown")
                args = json.dumps(tc.get("arguments", {}))[:100]
                result = str(tc.get("result", ""))[:100]
                
                console.print(f"[magenta]→ {name}[/magenta]")
                console.print(f"  Args: {args}")
                if result:
                    console.print(f"  Result: {result}")
        
        if follow:
            console.print("\n[yellow]Following logs... (Ctrl+C to stop)[/yellow]")
            last_msg_count = len(messages)
            last_tc_count = len(tool_calls)
            
            while True:
                time.sleep(2)
                response = client.get_run(run_id)
                if response.status_code == 200:
                    run_data = response.json()
                    
                    # Check if run is complete
                    if run_data.get("status") in ["completed", "failed", "cancelled"]:
                        console.print(f"\n[bold]Run {run_data.get('status')}[/bold]")
                        break
                    
                    # Show new messages
                    messages = run_data.get("messages", [])
                    for msg in messages[last_msg_count:]:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:200]
                        console.print(f"[{_role_color(role)}]{role}:[/{_role_color(role)}] {content}")
                    last_msg_count = len(messages)
                    
                    # Show new tool calls
                    tool_calls = run_data.get("tool_calls", [])
                    for tc in tool_calls[last_tc_count:]:
                        console.print(f"[magenta]→ {tc.get('name')}[/magenta]")
                    last_tc_count = len(tool_calls)
                    
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following.[/yellow]")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def _role_color(role: str) -> str:
    """Get color for message role."""
    colors = {
        "user": "cyan",
        "assistant": "green",
        "system": "yellow",
        "tool": "magenta"
    }
    return colors.get(role, "white")


@app.command()
def retry(
    run_id: str = typer.Argument(..., help="Run ID to retry"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion")
):
    """Retry a failed run with the same input."""
    client = get_api_client()
    
    try:
        # Get original run
        response = client.get_run(run_id)
        if response.status_code != 200:
            _handle_error(response, "getting run")
            return
        
        original = response.json()
        
        if original.get("status") not in ["failed", "cancelled"]:
            console.print(f"[yellow]Run is not in a retriable state (status: {original.get('status')})[/yellow]")
            return
        
        # Determine if it's an agent or workflow run
        if original.get("agent_id"):
            new_response = client.run_agent(
                original["agent_id"],
                original.get("input_message", ""),
                context_variables=original.get("context_variables")
            )
        elif original.get("workflow_id"):
            new_response = client.run_workflow(
                original["workflow_id"],
                original.get("input_message", ""),
                context_variables=original.get("context_variables")
            )
        else:
            console.print("[red]Error:[/red] Cannot determine run type for retry")
            return
        
        if new_response.status_code == 201:
            new_run = new_response.json()
            console.print(f"[green]Retry started![/green]")
            console.print(f"New Run ID: {new_run.get('id')}")
            
            if wait:
                import time
                console.print("\n[yellow]Waiting for completion...[/yellow]")
                while True:
                    time.sleep(2)
                    status_response = client.get_run(new_run["id"])
                    if status_response.status_code == 200:
                        run_status = status_response.json()
                        if run_status.get("status") in ["completed", "failed", "cancelled"]:
                            console.print(f"\n[bold]Final Status:[/bold] {run_status.get('status')}")
                            if run_status.get("output"):
                                console.print(f"[bold]Output:[/bold]\n{run_status['output']}")
                            if run_status.get("error"):
                                console.print(f"[red]Error:[/red] {run_status['error']}")
                            break
                    else:
                        break
        else:
            _handle_error(new_response, "starting retry")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
