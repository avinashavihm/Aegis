"""
File environment for file operations
"""

import os
from pathlib import Path
from typing import List, Optional
from aegis.config import WORKSPACE_DIR, LOCAL_ROOT


class FileEnv:
    """File system operations environment"""
    
    def __init__(self, workspace_name: str = "workspace"):
        self.workspace_name = workspace_name
        self.local_root = os.path.join(LOCAL_ROOT, WORKSPACE_DIR, workspace_name)
        os.makedirs(self.local_root, exist_ok=True)
    
    def read_file(self, file_path: str) -> str:
        """Read a file"""
        full_path = os.path.join(self.local_root, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def write_file(self, file_path: str, content: str) -> str:
        """Write a file"""
        full_path = os.path.join(self.local_root, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File written successfully: {full_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def list_files(self, directory: str = ".", recursive: bool = False) -> List[str]:
        """List files in a directory"""
        full_path = os.path.join(self.local_root, directory)
        files = []
        try:
            if recursive:
                for root, dirs, filenames in os.walk(full_path):
                    for filename in filenames:
                        rel_path = os.path.relpath(os.path.join(root, filename), self.local_root)
                        files.append(rel_path)
            else:
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    if os.path.isfile(item_path):
                        rel_path = os.path.relpath(item_path, self.local_root)
                        files.append(rel_path)
            return files
        except Exception as e:
            return [f"Error listing files: {str(e)}"]
    
    def search_files(self, pattern: str, directory: str = ".") -> List[str]:
        """Search for files matching a pattern"""
        import fnmatch
        files = self.list_files(directory, recursive=True)
        return [f for f in files if fnmatch.fnmatch(f, pattern)]

