"""
Local execution environment for Aegis
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional
from aegis.config import WORKSPACE_DIR, LOCAL_ROOT


class LocalEnv:
    """Local Python execution environment"""
    
    def __init__(self, workspace_name: str = "workspace"):
        self.workspace_name = workspace_name
        self.local_root = os.path.join(LOCAL_ROOT, WORKSPACE_DIR, workspace_name)
        os.makedirs(self.local_root, exist_ok=True)
    
    def run_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, any]:
        """
        Execute a shell command
        
        Args:
            command: Command to execute
            cwd: Working directory (defaults to workspace)
            
        Returns:
            Dictionary with 'status' (exit code) and 'result' (stdout/stderr)
        """
        if cwd is None:
            cwd = self.local_root
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return {
                "status": result.returncode,
                "result": result.stdout + result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "status": -1,
                "result": "Command timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "status": -1,
                "result": f"Error executing command: {str(e)}"
            }
    
    def run_python(self, code: str, cwd: Optional[str] = None) -> Dict[str, any]:
        """
        Execute Python code
        
        Args:
            code: Python code to execute
            cwd: Working directory
            
        Returns:
            Dictionary with 'status' and 'result'
        """
        if cwd is None:
            cwd = self.local_root
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=cwd) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ["python", temp_file],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "status": result.returncode,
                "result": result.stdout + result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "status": -1,
                "result": "Python execution timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "status": -1,
                "result": f"Error executing Python: {str(e)}"
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def create_file(self, file_path: str, content: str) -> Dict[str, any]:
        """
        Create a file in the workspace
        
        Args:
            file_path: Relative path from workspace root
            content: File content
            
        Returns:
            Dictionary with 'status' and 'message'
        """
        full_path = os.path.join(self.local_root, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {
                "status": 0,
                "message": f"File created successfully at: {full_path}"
            }
        except Exception as e:
            return {
                "status": -1,
                "message": f"Error creating file: {str(e)}"
            }
    
    def read_file(self, file_path: str) -> str:
        """Read a file from the workspace"""
        full_path = os.path.join(self.local_root, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

