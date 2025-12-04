"""
File System Connectors for knowledge grounding
"""

import os
import json
import csv
import glob
from typing import Dict, List, Any, Optional
from pathlib import Path

from aegis.knowledge.connector_registry import (
    BaseConnector, ConnectorConfig, ConnectorType, 
    ConnectionStatus, ConnectorRegistry
)


class FileSystemConnector(BaseConnector):
    """File system connector for reading local files"""
    
    connector_type = ConnectorType.FILE
    name = "FileSystem"
    description = "Connect to local file system"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.base_path = config.config.get("base_path", ".")
        self.allowed_extensions = config.config.get("allowed_extensions", ["*"])
        self.max_file_size = config.config.get("max_file_size", 10 * 1024 * 1024)  # 10MB
    
    def connect(self) -> bool:
        try:
            if os.path.exists(self.base_path):
                self._set_connected()
                return True
            else:
                self._set_error(f"Path does not exist: {self.base_path}")
                return False
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        params = params or {}
        
        # Parse query: read:path, list:path, search:term
        if ":" in query:
            action, target = query.split(":", 1)
            action = action.lower()
        else:
            action = "read"
            target = query
        
        if action == "read":
            return self._read_file(target)
        elif action == "list":
            return self._list_files(target, params.get("pattern", "*"))
        elif action == "search":
            return self._search_files(target, params.get("path", "."))
        elif action == "info":
            return self._get_file_info(target)
        else:
            return {"error": f"Unknown action: {action}"}
    
    def _read_file(self, path: str) -> Any:
        """Read file contents"""
        full_path = os.path.join(self.base_path, path)
        
        if not os.path.exists(full_path):
            return {"error": f"File not found: {path}"}
        
        if not os.path.isfile(full_path):
            return {"error": f"Not a file: {path}"}
        
        # Check file size
        if os.path.getsize(full_path) > self.max_file_size:
            return {"error": f"File too large: {path}"}
        
        # Check extension
        ext = os.path.splitext(path)[1].lower()
        if "*" not in self.allowed_extensions and ext not in self.allowed_extensions:
            return {"error": f"Extension not allowed: {ext}"}
        
        try:
            # Try to detect and parse special formats
            if ext == ".json":
                with open(full_path, 'r', encoding='utf-8') as f:
                    return {"content": json.load(f), "format": "json"}
            elif ext == ".csv":
                with open(full_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    return {"content": list(reader), "format": "csv"}
            else:
                with open(full_path, 'r', encoding='utf-8') as f:
                    return {"content": f.read(), "format": "text"}
        except UnicodeDecodeError:
            # Binary file
            return {"error": "Cannot read binary file as text"}
        except Exception as e:
            return {"error": str(e)}
    
    def _list_files(self, path: str, pattern: str = "*") -> List[Dict[str, Any]]:
        """List files in directory"""
        full_path = os.path.join(self.base_path, path)
        
        if not os.path.exists(full_path):
            return []
        
        files = []
        search_pattern = os.path.join(full_path, pattern)
        
        for file_path in glob.glob(search_pattern):
            if os.path.isfile(file_path):
                rel_path = os.path.relpath(file_path, self.base_path)
                files.append({
                    "path": rel_path,
                    "name": os.path.basename(file_path),
                    "size": os.path.getsize(file_path),
                    "extension": os.path.splitext(file_path)[1]
                })
        
        return files
    
    def _search_files(self, search_term: str, path: str = ".") -> List[Dict[str, Any]]:
        """Search for files containing term"""
        results = []
        full_path = os.path.join(self.base_path, path)
        
        for root, dirs, files in os.walk(full_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.base_path)
                
                # Check extension
                ext = os.path.splitext(file)[1].lower()
                if "*" not in self.allowed_extensions and ext not in self.allowed_extensions:
                    continue
                
                # Check file size
                if os.path.getsize(file_path) > self.max_file_size:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if search_term.lower() in content.lower():
                            # Find matching lines
                            lines = content.split('\n')
                            matches = [
                                {"line": i+1, "content": line.strip()}
                                for i, line in enumerate(lines)
                                if search_term.lower() in line.lower()
                            ][:5]  # Limit matches per file
                            
                            results.append({
                                "file": rel_path,
                                "matches": matches
                            })
                except:
                    continue
        
        return results
    
    def _get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file information"""
        full_path = os.path.join(self.base_path, path)
        
        if not os.path.exists(full_path):
            return {"error": f"Path not found: {path}"}
        
        stat = os.stat(full_path)
        
        return {
            "path": path,
            "name": os.path.basename(path),
            "is_file": os.path.isfile(full_path),
            "is_directory": os.path.isdir(full_path),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "extension": os.path.splitext(path)[1] if os.path.isfile(full_path) else None
        }
    
    def test_connection(self) -> bool:
        return os.path.exists(self.base_path)


class JSONFileConnector(BaseConnector):
    """JSON file connector for structured data"""
    
    connector_type = ConnectorType.FILE
    name = "JSONFile"
    description = "Connect to JSON files for structured queries"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.file_path = config.config.get("file_path", "")
        self._data: Optional[Any] = None
    
    def connect(self) -> bool:
        try:
            if not os.path.exists(self.file_path):
                self._set_error(f"File not found: {self.file_path}")
                return False
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            
            self._set_connected()
            return True
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        self._data = None
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if self._data is None:
            raise Exception("Not connected")
        
        params = params or {}
        
        # Handle search queries
        if query.startswith("search:"):
            search_term = query[7:]
            return self._search(search_term)
        
        # Handle JSONPath-like queries
        if query.startswith("$."):
            return self._jsonpath_query(query)
        
        # Simple key access
        if query in self._data if isinstance(self._data, dict) else False:
            return self._data[query]
        
        # Filter query
        if "filter:" in query:
            filter_expr = query.split("filter:")[1]
            return self._filter(filter_expr, params)
        
        return self._data
    
    def _jsonpath_query(self, path: str) -> Any:
        """Simple JSONPath query support"""
        # Remove $. prefix
        path = path[2:]
        parts = path.split(".")
        
        result = self._data
        for part in parts:
            if isinstance(result, dict):
                result = result.get(part)
            elif isinstance(result, list) and part.isdigit():
                result = result[int(part)]
            else:
                return None
        
        return result
    
    def _search(self, term: str) -> List[Any]:
        """Search for term in data"""
        results = []
        self._search_recursive(self._data, term.lower(), "", results)
        return results
    
    def _search_recursive(self, data: Any, term: str, path: str, results: List):
        """Recursively search data"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                if term in str(key).lower() or term in str(value).lower():
                    results.append({"path": current_path, "value": value})
                self._search_recursive(value, term, current_path, results)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                if term in str(item).lower():
                    results.append({"path": current_path, "value": item})
                self._search_recursive(item, term, current_path, results)
    
    def _filter(self, expr: str, params: Dict) -> List[Any]:
        """Filter list data"""
        if not isinstance(self._data, list):
            return []
        
        # Simple filter: field=value
        if "=" in expr:
            field, value = expr.split("=", 1)
            return [
                item for item in self._data
                if isinstance(item, dict) and str(item.get(field, "")) == value
            ]
        
        return self._data
    
    def test_connection(self) -> bool:
        return self._data is not None


class CSVFileConnector(BaseConnector):
    """CSV file connector for tabular data"""
    
    connector_type = ConnectorType.FILE
    name = "CSVFile"
    description = "Connect to CSV files for tabular queries"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.file_path = config.config.get("file_path", "")
        self.delimiter = config.config.get("delimiter", ",")
        self._data: List[Dict[str, str]] = []
        self._headers: List[str] = []
    
    def connect(self) -> bool:
        try:
            if not os.path.exists(self.file_path):
                self._set_error(f"File not found: {self.file_path}")
                return False
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                self._headers = reader.fieldnames or []
                self._data = list(reader)
            
            self._set_connected()
            return True
        except Exception as e:
            self._set_error(str(e))
            return False
    
    def disconnect(self) -> bool:
        self._data = []
        self._headers = []
        self.status = ConnectionStatus.DISCONNECTED
        return True
    
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        if not self._data:
            raise Exception("Not connected or empty file")
        
        params = params or {}
        
        # Handle search queries
        if query.startswith("search:"):
            search_term = query[7:]
            return self._search(search_term)
        
        # SQL-like select
        if query.lower().startswith("select"):
            return self._select_query(query, params)
        
        # Filter query
        if "filter:" in query:
            filter_expr = query.split("filter:")[1]
            return self._filter(filter_expr)
        
        # Return all data
        if query == "*" or query.lower() == "all":
            return {"headers": self._headers, "rows": self._data, "count": len(self._data)}
        
        # Return specific column
        if query in self._headers:
            return [row.get(query, "") for row in self._data]
        
        return {"headers": self._headers, "rows": self._data[:10], "total": len(self._data)}
    
    def _search(self, term: str) -> List[Dict]:
        """Search all columns for term"""
        term_lower = term.lower()
        results = []
        
        for i, row in enumerate(self._data):
            for col, value in row.items():
                if term_lower in str(value).lower():
                    results.append({"row": i, "column": col, "data": row})
                    break
        
        return results
    
    def _select_query(self, query: str, params: Dict) -> Any:
        """Simple SQL-like SELECT support"""
        # Very basic parsing
        query_lower = query.lower()
        
        # Extract columns
        if "select *" in query_lower:
            columns = self._headers
        else:
            # Extract column names between SELECT and FROM/WHERE
            select_part = query_lower.split("select")[1]
            if "from" in select_part:
                select_part = select_part.split("from")[0]
            elif "where" in select_part:
                select_part = select_part.split("where")[0]
            columns = [c.strip() for c in select_part.split(",")]
        
        # Filter with WHERE clause
        filtered_data = self._data
        if "where" in query_lower:
            where_part = query.split("WHERE")[1] if "WHERE" in query else query.split("where")[1]
            # Simple = filter
            if "=" in where_part:
                col, val = where_part.strip().split("=")
                col = col.strip().strip('"\'')
                val = val.strip().strip('"\'')
                filtered_data = [row for row in filtered_data if str(row.get(col, "")).lower() == val.lower()]
        
        # Limit
        limit = params.get("limit", 100)
        filtered_data = filtered_data[:limit]
        
        # Select columns
        if columns != self._headers:
            result = [{c: row.get(c, "") for c in columns} for row in filtered_data]
        else:
            result = filtered_data
        
        return {"rows": result, "count": len(result)}
    
    def _filter(self, expr: str) -> List[Dict]:
        """Filter rows by expression"""
        if "=" in expr:
            field, value = expr.split("=", 1)
            field = field.strip()
            value = value.strip()
            return [row for row in self._data if str(row.get(field, "")).lower() == value.lower()]
        return self._data
    
    def test_connection(self) -> bool:
        return len(self._data) > 0 or len(self._headers) > 0
    
    def get_schema(self) -> Dict[str, Any]:
        """Get CSV schema"""
        return {
            "headers": self._headers,
            "row_count": len(self._data),
            "sample": self._data[:3] if self._data else []
        }


# Register connectors
ConnectorRegistry.register_type(FileSystemConnector)
ConnectorRegistry.register_type(JSONFileConnector)
ConnectorRegistry.register_type(CSVFileConnector)

