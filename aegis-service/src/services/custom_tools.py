"""
Custom Tool Service - Create and manage user-defined tools
"""

import os
import json
import uuid
import importlib.util
import traceback
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from src.config import settings
from src.database import get_db_connection
from src.services.tool_registry import ToolRegistry, ToolDefinition, ToolParameter, ToolCategory, tool_registry


@dataclass
class CustomToolCreate:
    """Schema for creating a custom tool"""
    name: str
    description: str
    definition_type: str  # 'python' or 'json'
    definition: Optional[Dict[str, Any]] = None  # JSON definition
    code_content: Optional[str] = None  # Python code
    parameters: List[Dict[str, Any]] = None
    return_type: str = "any"
    config: Dict[str, Any] = None


class CustomToolService:
    """
    Service for creating, managing, and executing custom tools.
    Supports both Python code and JSON-defined tools.
    """
    
    def __init__(self):
        self.tools_dir = os.path.join(settings.workspace_dir, "custom_tools")
        os.makedirs(self.tools_dir, exist_ok=True)
    
    def create_tool(
        self,
        user_id: str,
        tool_data: CustomToolCreate
    ) -> Dict[str, Any]:
        """
        Create a new custom tool.
        
        Args:
            user_id: Owner user ID
            tool_data: Tool creation data
            
        Returns:
            Created tool record
        """
        # Validate tool data
        self._validate_tool_data(tool_data)
        
        tool_id = str(uuid.uuid4())
        code_file_path = None
        
        # If Python code, save to file
        if tool_data.definition_type == 'python' and tool_data.code_content:
            code_file_path = self._save_code_file(tool_id, tool_data.code_content)
        
        # Store in database
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO custom_tools (
                        id, name, description, definition_type, definition,
                        code_content, code_file_path, parameters, return_type,
                        config, owner_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, name, description, definition_type, definition,
                              code_content, code_file_path, parameters, return_type,
                              config, is_enabled, owner_id, created_at, updated_at
                    """,
                    (
                        tool_id,
                        tool_data.name,
                        tool_data.description,
                        tool_data.definition_type,
                        json.dumps(tool_data.definition) if tool_data.definition else None,
                        tool_data.code_content,
                        code_file_path,
                        json.dumps(tool_data.parameters or []),
                        tool_data.return_type,
                        json.dumps(tool_data.config or {}),
                        user_id
                    )
                )
                result = cur.fetchone()
                conn.commit()
        
        # Register in tool registry
        self._register_in_registry(result)
        
        return dict(result)
    
    def _validate_tool_data(self, tool_data: CustomToolCreate):
        """Validate tool data"""
        if not tool_data.name:
            raise ValueError("Tool name is required")
        
        if tool_data.definition_type not in ('python', 'json'):
            raise ValueError("definition_type must be 'python' or 'json'")
        
        if tool_data.definition_type == 'python':
            if not tool_data.code_content:
                raise ValueError("code_content is required for Python tools")
            if len(tool_data.code_content) > 20000:
                raise ValueError("Python tool code too large (limit 20KB)")
            # Validate Python syntax
            try:
                compile(tool_data.code_content, '<string>', 'exec')
            except SyntaxError as e:
                raise ValueError(f"Invalid Python syntax: {e}")
        
        if tool_data.definition_type == 'json':
            if not tool_data.definition:
                raise ValueError("definition is required for JSON tools")
            if isinstance(tool_data.definition, dict) and len(json.dumps(tool_data.definition)) > 20000:
                raise ValueError("JSON definition too large (limit 20KB)")
    
    def _save_code_file(self, tool_id: str, code_content: str) -> str:
        """Save Python code to a file"""
        file_path = os.path.join(self.tools_dir, f"{tool_id}.py")
        with open(file_path, 'w') as f:
            f.write(code_content)
        return file_path
    
    def _register_in_registry(self, tool_record: Dict[str, Any]):
        """Register a custom tool in the tool registry"""
        parameters = []
        if tool_record['parameters']:
            params = tool_record['parameters'] if isinstance(tool_record['parameters'], list) else json.loads(tool_record['parameters'])
            for p in params:
                parameters.append(ToolParameter(
                    name=p.get('name', ''),
                    type=p.get('type', 'string'),
                    description=p.get('description', ''),
                    required=p.get('required', True),
                    default=p.get('default')
                ))
        
        # Create wrapper function
        tool_id = str(tool_record['id'])
        wrapper_func = self._create_tool_wrapper(tool_record)
        
        tool_def = ToolDefinition(
            name=tool_record['name'],
            description=tool_record['description'] or '',
            category=ToolCategory.CUSTOM,
            function=wrapper_func,
            parameters=parameters,
            return_type=tool_record.get('return_type', 'any'),
            is_enabled=tool_record.get('is_enabled', True),
            source='custom',
            metadata={'tool_id': tool_id}
        )
        
        tool_registry.register(tool_def)
    
    def _create_tool_wrapper(self, tool_record: Dict[str, Any]) -> Callable:
        """Create a wrapper function for the custom tool"""
        definition_type = tool_record['definition_type']
        
        if definition_type == 'python':
            return self._create_python_wrapper(tool_record)
        else:
            return self._create_json_wrapper(tool_record)
    
    def _create_python_wrapper(self, tool_record: Dict[str, Any]) -> Callable:
        """Create a wrapper for Python-based tool"""
        code_content = tool_record.get('code_content', '')
        tool_name = tool_record['name']
        
        def wrapper(**kwargs):
            """Execute Python tool in sandboxed environment"""
            try:
                # Create isolated namespace
                namespace = {
                    '__builtins__': {
                        'print': print,
                        'len': len,
                        'str': str,
                        'int': int,
                        'float': float,
                        'bool': bool,
                        'list': list,
                        'dict': dict,
                        'tuple': tuple,
                        'set': set,
                        'range': range,
                        'enumerate': enumerate,
                        'zip': zip,
                        'map': map,
                        'filter': filter,
                        'sorted': sorted,
                        'min': min,
                        'max': max,
                        'sum': sum,
                        'abs': abs,
                        'round': round,
                        'isinstance': isinstance,
                        'type': type,
                        'Exception': Exception,
                        'ValueError': ValueError,
                        'TypeError': TypeError,
                    },
                    'json': __import__('json'),
                    'datetime': __import__('datetime'),
                    're': __import__('re'),
                    'math': __import__('math'),
                }
                
                # Add input arguments
                namespace['args'] = kwargs
                namespace['input'] = kwargs
                
                # Execute code
                exec(code_content, namespace)
                
                # Look for main function or result
                if 'main' in namespace and callable(namespace['main']):
                    return namespace['main'](**kwargs)
                elif 'run' in namespace and callable(namespace['run']):
                    return namespace['run'](**kwargs)
                elif 'execute' in namespace and callable(namespace['execute']):
                    return namespace['execute'](**kwargs)
                elif 'result' in namespace:
                    return namespace['result']
                else:
                    return {"status": "executed", "namespace_keys": list(namespace.keys())}
                    
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
        
        wrapper.__name__ = tool_name
        wrapper.__doc__ = tool_record.get('description', '')
        return wrapper
    
    def _create_json_wrapper(self, tool_record: Dict[str, Any]) -> Callable:
        """Create a wrapper for JSON-defined tool"""
        definition = tool_record.get('definition', {})
        if isinstance(definition, str):
            definition = json.loads(definition)
        
        tool_name = tool_record['name']
        action_type = definition.get('action_type', 'http')
        
        def wrapper(**kwargs):
            """Execute JSON-defined tool"""
            try:
                if action_type == 'http':
                    return self._execute_http_tool(definition, kwargs)
                elif action_type == 'transform':
                    return self._execute_transform_tool(definition, kwargs)
                elif action_type == 'aggregate':
                    return self._execute_aggregate_tool(definition, kwargs)
                else:
                    return {"status": "error", "error": f"Unknown action type: {action_type}"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        wrapper.__name__ = tool_name
        wrapper.__doc__ = tool_record.get('description', '')
        return wrapper
    
    def _execute_http_tool(self, definition: Dict, kwargs: Dict) -> Dict:
        """Execute HTTP-based tool"""
        import requests
        
        method = definition.get('method', 'GET').upper()
        url_template = definition.get('url', '')
        headers = definition.get('headers', {})
        
        # Substitute variables in URL
        url = url_template.format(**kwargs)
        
        if method == 'GET':
            response = requests.get(url, headers=headers, params=kwargs, timeout=30)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=kwargs, timeout=30)
        else:
            return {"status": "error", "error": f"Unsupported HTTP method: {method}"}
        
        return {
            "status": "success",
            "status_code": response.status_code,
            "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    
    def _execute_transform_tool(self, definition: Dict, kwargs: Dict) -> Dict:
        """Execute data transformation tool"""
        transform = definition.get('transform', {})
        input_data = kwargs.get('data', kwargs)
        
        # Apply transformations
        result = input_data
        for key, expr in transform.items():
            if expr.startswith('$'):
                # Simple variable reference
                var_name = expr[1:]
                if var_name in input_data:
                    result[key] = input_data[var_name]
        
        return {"status": "success", "result": result}
    
    def _execute_aggregate_tool(self, definition: Dict, kwargs: Dict) -> Dict:
        """Execute aggregation tool"""
        operation = definition.get('operation', 'sum')
        field = definition.get('field', '')
        data = kwargs.get('data', [])
        
        if not isinstance(data, list):
            return {"status": "error", "error": "Data must be a list"}
        
        values = [item.get(field, 0) for item in data if isinstance(item, dict)]
        
        if operation == 'sum':
            result = sum(values)
        elif operation == 'avg':
            result = sum(values) / len(values) if values else 0
        elif operation == 'count':
            result = len(values)
        elif operation == 'min':
            result = min(values) if values else None
        elif operation == 'max':
            result = max(values) if values else None
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}
        
        return {"status": "success", "result": result}
    
    def get_tool(self, user_id: str, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get a custom tool by ID"""
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, description, definition_type, definition,
                           code_content, code_file_path, parameters, return_type,
                           config, is_enabled, owner_id, created_at, updated_at
                    FROM custom_tools
                    WHERE id = %s
                    """,
                    (tool_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None
    
    def list_tools(self, user_id: str) -> List[Dict[str, Any]]:
        """List all custom tools accessible to user"""
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, description, definition_type,
                           parameters, return_type, is_enabled, owner_id,
                           created_at, updated_at
                    FROM custom_tools
                    ORDER BY created_at DESC
                    """
                )
                results = cur.fetchall()
                return [dict(r) for r in results]
    
    def update_tool(
        self,
        user_id: str,
        tool_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a custom tool"""
        allowed_fields = ['name', 'description', 'definition', 'code_content',
                         'parameters', 'return_type', 'config', 'is_enabled']
        
        update_parts = []
        params = []
        
        for field in allowed_fields:
            if field in updates:
                update_parts.append(f"{field} = %s")
                value = updates[field]
                if field in ('definition', 'parameters', 'config') and isinstance(value, (dict, list)):
                    value = json.dumps(value)
                params.append(value)
        
        if not update_parts:
            return None
        
        params.append(tool_id)
        
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE custom_tools
                    SET {', '.join(update_parts)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, name, description, definition_type, definition,
                              code_content, code_file_path, parameters, return_type,
                              config, is_enabled, owner_id, created_at, updated_at
                    """,
                    params
                )
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    # Re-register in tool registry
                    tool_registry.unregister(result['name'])
                    self._register_in_registry(dict(result))
                
                return dict(result) if result else None
    
    def delete_tool(self, user_id: str, tool_id: str) -> bool:
        """Delete a custom tool"""
        with get_db_connection(user_id) as conn:
            with conn.cursor() as cur:
                # Get tool name first for unregistering
                cur.execute("SELECT name, code_file_path FROM custom_tools WHERE id = %s", (tool_id,))
                tool = cur.fetchone()
                
                if not tool:
                    return False
                
                # Delete from database
                cur.execute("DELETE FROM custom_tools WHERE id = %s RETURNING id", (tool_id,))
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    # Unregister from tool registry
                    tool_registry.unregister(tool['name'])
                    
                    # Delete code file if exists
                    if tool['code_file_path'] and os.path.exists(tool['code_file_path']):
                        os.remove(tool['code_file_path'])
                    
                    return True
                return False
    
    def execute_tool(
        self,
        user_id: str,
        tool_id: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a custom tool directly"""
        tool = self.get_tool(user_id, tool_id)
        if not tool:
            return {"status": "error", "error": "Tool not found"}
        
        if not tool.get('is_enabled', True):
            return {"status": "error", "error": "Tool is disabled"}
        
        # Get the wrapper function
        wrapper = self._create_tool_wrapper(tool)
        
        # Execute
        return wrapper(**arguments)
    
    def load_all_custom_tools(self, user_id: str):
        """Load all custom tools into the registry"""
        tools = self.list_tools(user_id)
        for tool in tools:
            if tool.get('is_enabled', True):
                full_tool = self.get_tool(user_id, str(tool['id']))
                if full_tool:
                    self._register_in_registry(full_tool)


# Singleton instance
custom_tool_service = CustomToolService()
