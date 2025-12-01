import typer
import click
from rich.console import Console
from rich.table import Table
from typing import Optional
from src.api_client import get_api_client
from src.config import set_auth_token, set_default_output_format
from src.utils import OutputFormat, set_output_format
import httpx

app = typer.Typer()
console = Console()


@app.command()
def create(
    username: str,
    email: str = typer.Option(..., "--email", help="User email"),
    password: str = typer.Option(..., "--password", "-p", help="User password"),
    full_name: str = typer.Option(None, "--name", help="Full name")
):
    """Create a new user."""
    client = get_api_client()
    
    try:
        response = client.post("/auth/register", json={
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name
        })
        
        if response.status_code == 201:
            user = response.json()
            console.print(f"[green]User created successfully![/green] ID: {user['id']}")
        elif response.status_code == 400:
            console.print(f"[red]Error:[/red] {response.json()['detail']}")
        else:
            console.print(f"[red]Error creating user:[/red] {response.text}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def login(
    username: Optional[str] = typer.Option(None, "--username", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password")
):
    """Login to the system."""
    if not username:
        username = typer.prompt("Username")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    client = get_api_client()
    
    try:
        response = client.post("/auth/login", json={
            "username": username,
            "password": password
        })
        
        if response.status_code == 200:
            data = response.json()
            set_auth_token(data["access_token"])
            
            # Ask for default output format
            from src.utils import OutputFormat
            output_format = typer.prompt(
                "output", 
                default="text", 
                show_choices=False,
                type=click.Choice([f.value for f in OutputFormat], case_sensitive=False)
            )
            set_default_output_format(output_format)
            
            console.print(f"[green]Login successful![/green] Welcome, {username}.")
        elif response.status_code == 401:
            console.print("[red]Invalid username or password.[/red]")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error logging in:[/red] {e}")


@app.command(name="list")
@app.command(name="ls", hidden=True)
def list_users(
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """List all users."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get("/users")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        users = response.json()
        
        from src.utils import print_output
        print_output(
            users, 
            columns=["username", "id", "email", "full_name"],
            title="Users"
        )

    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error listing users:[/red] {e}")


@app.command()
def me(
    output: Optional[OutputFormat] = typer.Option(None, "--output", "-o", help="Output format")
):
    """Get current user information."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get("/auth/me")
        
        if response.status_code == 401:
            console.print("[red]Error:[/red] Not authenticated. Please login first.")
            return
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        user = response.json()
        
        from src.utils import print_output
        print_output(
            user,
            columns=["id", "username", "email", "full_name"],
            title="Current User"
        )
        
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def show_user(user_identifier: str, output: Optional[OutputFormat] = None):
    """Show user details by username or ID."""
    if output:
        set_output_format(output)
    client = get_api_client()
    
    try:
        response = client.get(f"/users/{user_identifier}")
        
        if response.status_code != 200:
            console.print(f"[red]Error:[/red] {response.text}")
            return
        
        user = response.json()
        
        from src.utils import current_output_format, print_output
        
        # For structured formats, output full data
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            print_output(user)
        else:
            # For text/table, show as single-row table with username first
            print_output(
                user,
                columns=["username", "id", "email", "full_name"]
            )
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
