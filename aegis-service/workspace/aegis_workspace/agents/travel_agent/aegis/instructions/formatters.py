"""
Output Formatters for structured agent outputs
"""

import json
from typing import Dict, List, Any, Optional, Union
from enum import Enum


class FormatType(str, Enum):
    """Supported format types"""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    TABLE = "table"
    CODE = "code"
    HTML = "html"
    CSV = "csv"
    YAML = "yaml"


class OutputFormatter:
    """
    Formatter for structuring agent outputs.
    Supports multiple output formats and validation.
    """
    
    def __init__(self, format_type: FormatType = FormatType.TEXT):
        """
        Initialize the formatter.
        
        Args:
            format_type: The output format type
        """
        self.format_type = format_type
        self._schema: Optional[Dict[str, Any]] = None
        self._template: Optional[str] = None
    
    def set_schema(self, schema: Dict[str, Any]) -> 'OutputFormatter':
        """
        Set the output schema for validation.
        
        Args:
            schema: JSON schema for validation
        """
        self._schema = schema
        return self
    
    def set_template(self, template: str) -> 'OutputFormatter':
        """
        Set a template for formatting.
        
        Args:
            template: Format template with placeholders
        """
        self._template = template
        return self
    
    def format(self, data: Any) -> str:
        """
        Format data according to the format type.
        
        Args:
            data: Data to format
            
        Returns:
            Formatted string
        """
        formatters = {
            FormatType.TEXT: self._format_text,
            FormatType.JSON: self._format_json,
            FormatType.MARKDOWN: self._format_markdown,
            FormatType.TABLE: self._format_table,
            FormatType.CODE: self._format_code,
            FormatType.HTML: self._format_html,
            FormatType.CSV: self._format_csv,
            FormatType.YAML: self._format_yaml
        }
        
        formatter = formatters.get(self.format_type, self._format_text)
        return formatter(data)
    
    def _format_text(self, data: Any) -> str:
        """Format as plain text"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            lines = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        elif isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)
    
    def _format_json(self, data: Any) -> str:
        """Format as JSON"""
        if isinstance(data, str):
            try:
                # Try to parse if it's already JSON
                parsed = json.loads(data)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                return json.dumps({"content": data}, indent=2)
        return json.dumps(data, indent=2, default=str)
    
    def _format_markdown(self, data: Any) -> str:
        """Format as Markdown"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, list):
                    lines.append(f"## {key}")
                    for item in value:
                        lines.append(f"- {item}")
                elif isinstance(value, dict):
                    lines.append(f"## {key}")
                    for k, v in value.items():
                        lines.append(f"- **{k}**: {v}")
                else:
                    lines.append(f"**{key}**: {value}")
            return "\n\n".join(lines)
        elif isinstance(data, list):
            return "\n".join(f"- {item}" for item in data)
        return str(data)
    
    def _format_table(self, data: Any) -> str:
        """Format as ASCII table"""
        if not isinstance(data, list) or not data:
            return str(data)
        
        if isinstance(data[0], dict):
            # Table from list of dicts
            headers = list(data[0].keys())
            rows = [[str(row.get(h, "")) for h in headers] for row in data]
        elif isinstance(data[0], (list, tuple)):
            # Table from list of lists
            headers = [f"Col{i+1}" for i in range(len(data[0]))]
            rows = [[str(cell) for cell in row] for row in data]
        else:
            # Simple list
            return "\n".join(str(item) for item in data)
        
        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))
        
        # Build table
        lines = []
        
        # Header
        header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append("-+-".join("-" * w for w in widths))
        
        # Rows
        for row in rows:
            row_line = " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
            lines.append(row_line)
        
        return "\n".join(lines)
    
    def _format_code(self, data: Any) -> str:
        """Format as code block"""
        if isinstance(data, dict):
            language = data.get("language", "")
            code = data.get("code", str(data))
            return f"```{language}\n{code}\n```"
        return f"```\n{data}\n```"
    
    def _format_html(self, data: Any) -> str:
        """Format as HTML"""
        if isinstance(data, str):
            return f"<p>{data}</p>"
        elif isinstance(data, dict):
            html_parts = []
            for key, value in data.items():
                if isinstance(value, list):
                    html_parts.append(f"<h2>{key}</h2>")
                    html_parts.append("<ul>")
                    for item in value:
                        html_parts.append(f"  <li>{item}</li>")
                    html_parts.append("</ul>")
                else:
                    html_parts.append(f"<p><strong>{key}:</strong> {value}</p>")
            return "\n".join(html_parts)
        elif isinstance(data, list):
            items = "\n".join(f"  <li>{item}</li>" for item in data)
            return f"<ul>\n{items}\n</ul>"
        return f"<p>{data}</p>"
    
    def _format_csv(self, data: Any) -> str:
        """Format as CSV"""
        if not isinstance(data, list) or not data:
            return str(data)
        
        lines = []
        
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            lines.append(",".join(f'"{h}"' for h in headers))
            for row in data:
                values = [str(row.get(h, "")).replace('"', '""') for h in headers]
                lines.append(",".join(f'"{v}"' for v in values))
        elif isinstance(data[0], (list, tuple)):
            for row in data:
                values = [str(cell).replace('"', '""') for cell in row]
                lines.append(",".join(f'"{v}"' for v in values))
        else:
            for item in data:
                lines.append(f'"{str(item).replace(chr(34), chr(34)+chr(34))}"')
        
        return "\n".join(lines)
    
    def _format_yaml(self, data: Any) -> str:
        """Format as YAML"""
        def _to_yaml(obj: Any, indent: int = 0) -> str:
            prefix = "  " * indent
            
            if isinstance(obj, dict):
                lines = []
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        lines.append(f"{prefix}{key}:")
                        lines.append(_to_yaml(value, indent + 1))
                    else:
                        lines.append(f"{prefix}{key}: {value}")
                return "\n".join(lines)
            elif isinstance(obj, list):
                lines = []
                for item in obj:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{prefix}-")
                        lines.append(_to_yaml(item, indent + 1))
                    else:
                        lines.append(f"{prefix}- {item}")
                return "\n".join(lines)
            else:
                return f"{prefix}{obj}"
        
        return _to_yaml(data)
    
    def get_format_instruction(self) -> str:
        """
        Get instruction text describing the expected format.
        
        Returns:
            Format instruction string
        """
        instructions = {
            FormatType.TEXT: "Respond in plain text format.",
            FormatType.JSON: "Respond in valid JSON format. Ensure all strings are properly quoted and the JSON is parseable.",
            FormatType.MARKDOWN: "Respond in Markdown format. Use headers, lists, and formatting as appropriate.",
            FormatType.TABLE: "Respond with data in table format using | separators and - for header separation.",
            FormatType.CODE: "Respond with code in a code block using triple backticks and language identifier.",
            FormatType.HTML: "Respond in HTML format with appropriate tags.",
            FormatType.CSV: "Respond in CSV format with quoted values and commas as separators.",
            FormatType.YAML: "Respond in YAML format with proper indentation."
        }
        
        instruction = instructions.get(self.format_type, "Respond appropriately.")
        
        if self._schema:
            instruction += f"\n\nExpected schema:\n{json.dumps(self._schema, indent=2)}"
        
        if self._template:
            instruction += f"\n\nUse this template:\n{self._template}"
        
        return instruction
    
    def validate(self, output: str) -> tuple[bool, Optional[str]]:
        """
        Validate output against the format and schema.
        
        Args:
            output: Output string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.format_type == FormatType.JSON:
            try:
                parsed = json.loads(output)
                if self._schema:
                    # Basic schema validation
                    return self._validate_schema(parsed, self._schema)
                return True, None
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {str(e)}"
        
        # For other formats, basic validation
        if not output or not output.strip():
            return False, "Output is empty"
        
        return True, None
    
    def _validate_schema(self, data: Any, schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Basic JSON schema validation"""
        if "type" in schema:
            expected_type = schema["type"]
            type_map = {
                "object": dict,
                "array": list,
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool
            }
            
            expected = type_map.get(expected_type)
            if expected and not isinstance(data, expected):
                return False, f"Expected type {expected_type}, got {type(data).__name__}"
        
        if "properties" in schema and isinstance(data, dict):
            for prop, prop_schema in schema["properties"].items():
                if prop in data:
                    valid, error = self._validate_schema(data[prop], prop_schema)
                    if not valid:
                        return False, f"Property '{prop}': {error}"
        
        if "required" in schema and isinstance(data, dict):
            for required_prop in schema["required"]:
                if required_prop not in data:
                    return False, f"Missing required property: {required_prop}"
        
        return True, None


class FormatRegistry:
    """Registry for custom formatters"""
    
    _formatters: Dict[str, OutputFormatter] = {}
    
    @classmethod
    def register(cls, name: str, formatter: OutputFormatter):
        """Register a custom formatter"""
        cls._formatters[name] = formatter
    
    @classmethod
    def get(cls, name: str) -> Optional[OutputFormatter]:
        """Get a registered formatter"""
        return cls._formatters.get(name)
    
    @classmethod
    def list_formatters(cls) -> List[str]:
        """List all registered formatters"""
        return list(cls._formatters.keys())


# Pre-register common formatters
FormatRegistry.register("json", OutputFormatter(FormatType.JSON))
FormatRegistry.register("markdown", OutputFormatter(FormatType.MARKDOWN))
FormatRegistry.register("table", OutputFormatter(FormatType.TABLE))
FormatRegistry.register("csv", OutputFormatter(FormatType.CSV))

