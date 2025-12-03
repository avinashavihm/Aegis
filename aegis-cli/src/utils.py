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

def format_column_name(col: str) -> str:
    """Format column name for display with proper capitalization."""
    # Handle special patterns like *_id
    parts = col.split('_')
    formatted_parts = []
    for part in parts:
        if part.upper() == 'ID':
            formatted_parts.append('ID')
        else:
            formatted_parts.append(part.title())
    return '_'.join(formatted_parts)

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
    
    # If columns not provided, try to get them from first item
    if not columns:
        if data:
            columns = list(data[0].keys())
        else:
            # No data and no columns specified
            console.print("No data found.")
            return

    # Show table with headers even if no data
    if current_output_format == OutputFormat.TABLE:
        table = Table(title=title)
        for col in columns:
            table.add_column(format_column_name(col), style="cyan")
        
        if data:
            for item in data:
                row = [str(item.get(col, "")) for col in columns]
                table.add_row(*row)
        
        console.print(table)
        
    elif current_output_format == OutputFormat.TEXT:
        # Aligned text output using rich Table with no borders
        # No title for text output as requested
        table = Table(box=None, show_header=True, padding=(0, 2, 0, 0), title=None, pad_edge=False)
        for col in columns:
            table.add_column(format_column_name(col), header_style="bold")
        
        if data:
            for item in data:
                row = [str(item.get(col, "")) for col in columns]
                table.add_row(*row)
            
        console.print(table)
