import json
import typer
from rich.console import Console
from rich.table import Table
from typing import List, Dict, Any, Optional
from enum import Enum

console = Console()

class OutputFormat(str, Enum):
    JSON = "json"
    TABLE = "table"
    TEXT = "text"
    YAML = "yaml"

# Global state for output format
current_output_format = OutputFormat.TABLE

def set_output_format(format: OutputFormat):
    global current_output_format
    current_output_format = format

def print_output(data: Any, columns: List[str] = None, title: str = None):
    """
    Print data in the selected format.
    
    Args:
        data: The data to print (list of dicts or single dict)
        columns: List of column names for table/text output
        title: Title for the table
    """
    if current_output_format == OutputFormat.JSON:
        console.print_json(data=data)
        return
        
    if current_output_format == OutputFormat.YAML:
        import yaml
        from rich.syntax import Syntax
        yaml_str = yaml.dump(data, sort_keys=False)
        syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
        console.print(syntax)
        return

    # Ensure data is a list for table/text processing
    if isinstance(data, dict):
        data = [data]
    
    if not data:
        console.print("No data found.")
        return

    # If columns not provided, use keys from first item
    if not columns and data:
        columns = list(data[0].keys())

    if current_output_format == OutputFormat.TABLE:
        table = Table(title=title)
        for col in columns:
            table.add_column(col.replace("_", " ").title(), style="cyan")
        
        for item in data:
            row = [str(item.get(col, "")) for col in columns]
            table.add_row(*row)
        
        console.print(table)
        
    elif current_output_format == OutputFormat.TEXT:
        # Aligned text output using rich Table with no borders
        # No title for text output as requested
        table = Table(box=None, show_header=True, padding=(0, 2), title=None)
        for col in columns:
            table.add_column(col.replace("_", " ").title(), header_style="bold")
        
        for item in data:
            row = [str(item.get(col, "")) for col in columns]
            table.add_row(*row)
            
        console.print(table)
