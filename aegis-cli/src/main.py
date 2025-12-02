import typer
from src.commands import user, team, role, policy
from src.commands.user import login
from src.utils import OutputFormat, set_output_format

app = typer.Typer(
    name="aegis",
    help="Agentic Ops CLI Tool",
    add_completion=False,
    no_args_is_help=True
)

@app.callback()
def main(
    output: OutputFormat = typer.Option(
        None,
        "--output",
        "-o",
        help="Output format (json, table, text). Default: text"
    )
):
    """
    Aegis CLI - Agentic Ops Platform
    """
    if output is None:
        from src.config import get_default_output_format
        output = OutputFormat(get_default_output_format())
        
    set_output_format(output)

app.add_typer(user.app, name="user", help="Manage users")
app.add_typer(team.app, name="team", help="Manage teams")
app.add_typer(role.app, name="role", help="Manage roles")
app.add_typer(policy.app, name="policy", help="Manage policies")
app.command()(login)

@app.command()
def get(
    resource_type: str = typer.Argument(..., help="Resource type (role/roles, team/teams, user/users, policy/policies)"),
    identifier: str = typer.Argument(None, help="Resource identifier (name or ID) - omit to list all"),
    output: OutputFormat = typer.Option(None, "--output", "-o", help="Output format")
):
    """Get details of a specific resource or list all resources."""
    if output:
        set_output_format(output)
    
    resource_type = resource_type.lower()
    
    # Normalize shorthand aliases
    alias_map = {
        "ws": "teams",  # ws alias kept for backward compatibility/muscle memory, maps to teams
        "wss": "teams",
        "teams": "teams",
        "team": "team",
        "policies": "policies",
        "policy": "policy"
    }
    resource_type = alias_map.get(resource_type, resource_type)
    
    # Handle plural forms for listing
    if resource_type == "roles":
        from src.commands.role import list_roles
        list_roles(team=False, output=output)
    elif resource_type == "role":
        if not identifier:
            # Default to listing all roles
            from src.commands.role import list_roles
            list_roles(team=False, output=output)
        else:
            from src.commands.role import show_role
            show_role(identifier, output)
    elif resource_type == "teams":
        from src.commands.team import list_teams
        list_teams(output=output)
    elif resource_type == "team":
        if not identifier:
            # Default to listing all teams
            from src.commands.team import list_teams
            list_teams(output=output)
        else:
            from src.commands.team import show_team
            show_team(identifier, output)
    elif resource_type == "policies":
        from src.commands.policy import list_policies
        list_policies(output=output)
    elif resource_type == "policy":
        if not identifier:
            # Default to listing all policies
            from src.commands.policy import list_policies
            list_policies(output=output)
        else:
            from src.commands.policy import show_policy
            show_policy(identifier, output)
    elif resource_type == "users":
        from src.commands.user import list_users
        list_users(output=output)
    elif resource_type == "user":
        from src.commands.user import show_user, me
        if not identifier:
            # Default to current user
            me(output)
        else:
            show_user(identifier, output)
    else:
        typer.echo(f"Unknown resource type: {resource_type}")
        typer.echo("Valid types: role/roles, team/teams/ws, user/users, policy/policies")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
