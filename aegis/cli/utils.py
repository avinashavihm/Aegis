"""
CLI utilities for prompts and menus
"""

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from typing import List, Optional

console = Console()


def print_logo():
    """Print Aegis logo"""
    logo = """
    ╔═══════════════════════════════════╗
    ║          AEGIS AGENT              ║
    ║      Simplified LLM Framework     ║
    ╚═══════════════════════════════════╝
    """
    console.print(Panel(logo, style="bold blue", expand=False))


def single_select_menu(options: List[str], prompt_text: str = "Select an option:") -> str:
    """
    Display a single-select menu and return the selected option.
    
    Args:
        options: List of option strings
        prompt_text: Prompt text to display
        
    Returns:
        Selected option string
    """
    console.print(f"\n[bold cyan]{prompt_text}[/bold cyan]")
    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option}")
    
    while True:
        try:
            choice = Prompt.ask("\nEnter your choice", default="1")
            choice_num = int(choice)
            if 1 <= choice_num <= len(options):
                return options[choice_num - 1]
            else:
                console.print(f"[red]Invalid choice. Please enter a number between 1 and {len(options)}.[/red]")
        except ValueError:
            console.print("[red]Invalid input. Please enter a number.[/red]")


def ask_text(prompt_text: str, default: Optional[str] = None) -> str:
    """Ask for text input"""
    return Prompt.ask(prompt_text, default=default)


def print_success(message: str):
    """Print success message"""
    console.print(f"[green]✓ {message}[/green]")


def print_error(message: str):
    """Print error message"""
    console.print(f"[red]✗ {message}[/red]")


def print_info(message: str):
    """Print info message"""
    console.print(f"[blue]ℹ {message}[/blue]")

