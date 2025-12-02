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


def list_users(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output format: json, yaml, wide")
):
    """List all users."""
    from src.utils import print_output, current_output_format, OutputFormat
    
    # Determine if wide mode
    wide_mode = False
    if output:
        if output.lower() == "wide":
            wide_mode = True
            # Set to default text format for wide
            from src.config import get_default_output_format
            default_format = get_default_output_format()
            set_output_format(OutputFormat(default_format))
        else:
            # Handle json, yaml, text, table
            try:
                set_output_format(OutputFormat(output.lower()))
            except ValueError:
                console.print(f"[red]Error:[/red] Invalid output format: {output}")
                console.print("Valid formats: json, yaml, wide")
                return
    
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
        
        # For structured formats, remove IDs
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_users = []
            for user in users:
                clean_u = {
                    "username": user["username"],
                    "email": user["email"],
                    "full_name": user.get("full_name", ""),
                    "teams": [{"name": t.get('team_name', ''), "role": t.get('role_name', '')} for t in user.get('teams', [])],
                    "roles": [r['name'] for r in user.get('roles', [])]
                }
                clean_users.append(clean_u)
            print_output(clean_users, title="Users")
        else:
            # For table/text view, format the data
            display_users = []
            for user in users:
                # Format teams (just team names, no roles)
                teams_str = ", ".join([t['team_name'] for t in user.get('teams', [])])
                
                # Format direct roles
                user_roles_str = ", ".join([r['name'] for r in user.get('roles', [])])

                display_users.append({
                    "username": user["username"],
                    "teams": teams_str or "-",
                    "user_roles": user_roles_str or "-",
                    "user_id": user["id"],
                    "email": user["email"],
                    "full_name": user.get("full_name", "")
                })
            
            # Choose columns based on wide mode
            if wide_mode:
                columns = ["username", "teams", "user_roles", "email", "full_name", "user_id"]
            else:
                columns = ["username", "teams", "user_roles"]
            
            print_output(
                display_users, 
                columns=columns,
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
        
        from src.utils import print_output, current_output_format
        
        # For structured formats, remove IDs
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_user = {
                "username": user["username"],
                "email": user["email"],
                "full_name": user.get("full_name", ""),
                "teams": [{"name": t.get('name', ''), "role": t.get('role_name', '')} for t in user.get('teams', [])],
                "roles": [r['name'] for r in user.get('roles', [])]
            }
            print_output(clean_user)
        else:
            # Format teams and roles like in show_user
            teams_str = ", ".join([t.get('team_name', t.get('name', '')) for t in user.get('teams', [])])
            user_roles_str = ", ".join([r['name'] for r in user.get('roles', [])])
            
            display_user = {
                "username": user["username"],
                "teams": teams_str or "-",
                "user_roles": user_roles_str or "-",
                "email": user["email"],
                "full_name": user.get("full_name", "")
            }
            
            print_output(
                display_user,
                columns=["username", "teams", "user_roles", "email", "full_name"],
                title="Current User"
            )
            
            # Show detailed team roles if present
            if "teams" in user and user["teams"]:
                console.print("\n[bold]Team Roles:[/bold]")
                print_output(
                    user["teams"],
                    columns=["name", "role_name"],
                    title=None
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
        
        # For structured formats, remove IDs
        if current_output_format in [OutputFormat.JSON, OutputFormat.YAML]:
            clean_user = {
                "username": user["username"],
                "email": user["email"],
                "full_name": user.get("full_name", ""),
                "teams": [{"name": t.get('name', ''), "role": t.get('role_name', '')} for t in user.get('teams', [])],
                "roles": [r['name'] for r in user.get('roles', [])]
            }
            print_output(clean_user)
        else:
            # Format teams and roles like in list view
            teams_str = ", ".join([t.get('team_name', t.get('name', '')) for t in user.get('teams', [])])
            user_roles_str = ", ".join([r['name'] for r in user.get('roles', [])])
            
            display_user = {
                "username": user["username"],
                "teams": teams_str or "-",
                "user_roles": user_roles_str or "-",
                "email": user["email"],
                "full_name": user.get("full_name", ""),
                "user_id": user["id"]
            }
            
            # For text/table, show as single-row table with username first
            print_output(
                display_user,
                columns=["username", "teams", "user_roles", "email", "full_name"]
            )
            
            # Show detailed team roles if present
            if "teams" in user and user["teams"]:
                console.print("\n[bold]Team Roles:[/bold]")
                print_output(
                    user["teams"],
                    columns=["name", "role_name"],
                    title=None
                )
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="assign-role")
def assign_role(
    user_identifier: str = typer.Argument(..., help="Username or user ID"),
    role_identifier: str = typer.Argument(..., help="Role name or ID")
):
    """Assign a role directly to a user (not through team membership)."""
    client = get_api_client()
    
    try:
        response = client.post(f"/users/{user_identifier}/roles/{role_identifier}", json={})
        
        if response.status_code == 200:
            console.print(f"[green]Role assigned successfully![/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] User or role not found")
        elif response.status_code == 409:
            console.print(f"[red]Error:[/red] Role already assigned to this user")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="remove-role")
def remove_role(
    user_identifier: str = typer.Argument(..., help="Username or user ID"),
    role_identifier: str = typer.Argument(..., help="Role name or ID")
):
    """Remove a directly assigned role from a user."""
    client = get_api_client()
    
    if not typer.confirm(f"Remove role from user {user_identifier}?"):
        return
    
    try:
        response = client.delete(f"/users/{user_identifier}/roles/{role_identifier}")
        
        if response.status_code == 204:
            console.print(f"[green]Role removed successfully.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] User, role, or assignment not found")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command(name="change-password")
def change_password(
    user_identifier: Optional[str] = typer.Argument(None, help="Username or user ID (optional, defaults to current user)"),
    new_password: Optional[str] = typer.Option(None, "--password", "-p", help="New password (will be prompted if not provided)")
):
    """Change password for a user (admin can change any, users can change their own)."""
    client = get_api_client()
    
    # If no user specified, change current user's password
    if not user_identifier:
        try:
            response = client.get("/auth/me")
            if response.status_code == 200:
                current_user = response.json()
                user_identifier = current_user["username"]
            else:
                console.print("[red]Error:[/red] Could not get current user")
                return
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            return
    
    # Prompt for password if not provided
    if not new_password:
        new_password = typer.prompt("New password", hide_input=True)
        confirm_password = typer.prompt("Confirm password", hide_input=True)
        if new_password != confirm_password:
            console.print("[red]Error:[/red] Passwords do not match")
            return
    
    try:
        response = client.put(f"/users/{user_identifier}", json={
            "password": new_password
        })
        
        if response.status_code == 200:
            console.print(f"[green]Password changed successfully for user '{user_identifier}'.[/green]")
        elif response.status_code == 404:
            console.print(f"[red]Error:[/red] User not found")
        elif response.status_code == 403:
            console.print(f"[red]Error:[/red] Access denied. You can only change your own password unless you're an admin.")
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            
    except httpx.ConnectError:
        console.print("[red]Error:[/red] Cannot connect to API. Is the service running?")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

