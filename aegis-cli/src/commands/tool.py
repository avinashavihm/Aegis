"""
Tools management commands - list available tools, custom tools CRUD
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
def list_tools(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    custom_only: bool = typer.Option(False, "--custom", help="Show only custom tools"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml, wide")
):
    """List all available tools."""
    if output and output.lower() not in ["wide"]:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    wide_mode = output and output.lower() == "wide"
    client = get_api_client()
    
    try:
        if custom_only:
            response = client.list_custom_tools()
            if response.status_code != 200:
                _handle_error(response, "listing custom tools")
                return
            
            tools = response.json()
            if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
                print_output(tools, title="Custom Tools")
            else:
                display_tools = []
                for t in tools:
                    item = {
                        "name": t.get("name", ""),
                        "description": (t.get("description") or "")[:50],
                        "type": t.get("tool_type", ""),
                    }
                    if wide_mode:
                        item["id"] = str(t.get("id", ""))[:8]
                    display_tools.append(item)
                
                columns = ["name", "description", "type"]
                if wide_mode:
                    columns.append("id")
                
                print_output(display_tools, columns=columns, title="Custom Tools")
        else:
            response = client.list_tools(category=category)
            if response.status_code != 200:
                _handle_error(response, "listing tools")
                return
            
            data = response.json()
            tools = data.get("tools", [])
            categories = data.get("categories", [])
            
            if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
                clean_tools = []
                for t in tools:
                    clean_tools.append(remove_ids_recursive({
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "category": t.get("category", ""),
                        "source": t.get("source", ""),
                        "parameters": t.get("parameters", [])
                    }))
                print_output({"tools": clean_tools, "categories": categories})
            else:
                display_tools = []
                for t in tools:
                    params_count = len(t.get("parameters", []))
                    item = {
                        "name": t.get("name", ""),
                        "category": t.get("category", "") or "-",
                        "source": t.get("source", "") or "builtin",
                        "params": str(params_count)
                    }
                    if wide_mode:
                        item["description"] = (t.get("description") or "")[:60]
                    display_tools.append(item)
                
                columns = ["name", "category", "source", "params"]
                if wide_mode:
                    columns.append("description")
                
                print_output(display_tools, columns=columns, title=f"Available Tools ({len(tools)})")
                
                if categories and not category:
                    console.print(f"\n[dim]Categories: {', '.join(categories)}[/dim]")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="get")
@app.command(name="show")
def show_tool(
    tool_name: str = typer.Argument(..., help="Tool name"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Show tool details and parameters."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.get_tool(tool_name)
        
        if response.status_code != 200:
            _handle_error(response, "getting tool")
            return
        
        tool = response.json()
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(tool)
        else:
            console.print(f"\n[bold cyan]Tool:[/bold cyan] {tool.get('name', '')}")
            console.print(f"[bold]Category:[/bold] {tool.get('category', '-')}")
            console.print(f"[bold]Source:[/bold] {tool.get('source', 'builtin')}")
            
            if tool.get("description"):
                console.print(f"[bold]Description:[/bold] {tool['description']}")
            
            params = tool.get("parameters", [])
            if params:
                console.print(f"\n[bold]Parameters ({len(params)}):[/bold]")
                for p in params:
                    required = " [red]*[/red]" if p.get("required") else ""
                    console.print(f"  • {p.get('name', '')}{required}: {p.get('type', 'string')}")
                    if p.get("description"):
                        console.print(f"    {p['description'][:80]}")
            
            metadata = tool.get("metadata", {})
            if metadata:
                console.print(f"\n[bold]Metadata:[/bold]")
                console.print_json(data=metadata)
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="categories")
def list_categories():
    """List available tool categories."""
    client = get_api_client()
    
    try:
        response = client.list_tools()
        
        if response.status_code != 200:
            _handle_error(response, "listing tools")
            return
        
        data = response.json()
        categories = data.get("categories", [])
        tools = data.get("tools", [])
        
        # Count tools per category
        cat_counts = {}
        for t in tools:
            cat = t.get("category") or "uncategorized"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        
        console.print("\n[bold]Tool Categories:[/bold]")
        for cat in sorted(categories):
            count = cat_counts.get(cat, 0)
            console.print(f"  • {cat}: {count} tools")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="create-custom")
def create_custom_tool(
    name: str = typer.Argument(..., help="Custom tool name"),
    description: str = typer.Option(..., "--desc", "-d", help="Tool description"),
    tool_type: str = typer.Option("http", "--type", "-t", help="Tool type (http, function, mcp)"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="JSON config file"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", help="HTTP endpoint URL (for http type)"),
    method: str = typer.Option("POST", "--method", "-m", help="HTTP method (for http type)"),
    parameters: Optional[str] = typer.Option(None, "--params", "-p", help="Parameters as JSON array")
):
    """Create a new custom tool."""
    client = get_api_client()
    
    payload = {
        "name": name,
        "description": description,
        "tool_type": tool_type
    }
    
    # Load from config file if provided
    if config_file:
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                payload.update(config)
        except Exception as e:
            console.print(f"[red]Error reading config file:[/red] {e}")
            return
    else:
        # Build config from options
        if tool_type == "http":
            if not endpoint:
                console.print("[red]Error:[/red] --endpoint is required for http type tools")
                return
            payload["config"] = {
                "endpoint": endpoint,
                "method": method
            }
        
        if parameters:
            try:
                payload["parameters"] = json.loads(parameters)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error parsing parameters JSON:[/red] {e}")
                return
    
    try:
        response = client.create_custom_tool(payload)
        
        if response.status_code == 201:
            tool = response.json()
            console.print(f"[green]Custom tool '{name}' created successfully![/green]")
            console.print(f"ID: {tool.get('id')}")
        else:
            _handle_error(response, "creating custom tool")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="delete-custom")
def delete_custom_tool(
    tool_id: str = typer.Argument(..., help="Custom tool ID"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt")
):
    """Delete a custom tool."""
    client = get_api_client()
    
    if not yes and not typer.confirm(f"Are you sure you want to delete custom tool '{tool_id}'?"):
        return
    
    try:
        response = client.delete_custom_tool(tool_id)
        
        if response.status_code == 204:
            console.print(f"[green]Custom tool deleted successfully.[/green]")
        else:
            _handle_error(response, "deleting custom tool")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="search")
def search_tools(
    query: str = typer.Argument(..., help="Search query"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml")
):
    """Search tools by name or description."""
    if output:
        try:
            set_output_format(OutputFormat(output.lower()))
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid output format: {output}")
            return
    
    client = get_api_client()
    
    try:
        response = client.list_tools()
        
        if response.status_code != 200:
            _handle_error(response, "listing tools")
            return
        
        data = response.json()
        tools = data.get("tools", [])
        
        # Filter by query
        query_lower = query.lower()
        matches = []
        for t in tools:
            name = (t.get("name") or "").lower()
            desc = (t.get("description") or "").lower()
            cat = (t.get("category") or "").lower()
            
            if query_lower in name or query_lower in desc or query_lower in cat:
                matches.append(t)
        
        if not matches:
            console.print(f"[yellow]No tools found matching '{query}'[/yellow]")
            return
        
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(matches)
        else:
            display_tools = []
            for t in matches:
                display_tools.append({
                    "name": t.get("name", ""),
                    "category": t.get("category", "") or "-",
                    "description": (t.get("description") or "")[:50]
                })
            
            print_output(display_tools, columns=["name", "category", "description"],
                        title=f"Search Results ({len(matches)} matches)")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
