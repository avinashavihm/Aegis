"""
Agent Sandbox - Run generated agents in isolated environments

Supports both local Docker sandboxes and cloud-based E2B sandboxes.
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import queue

from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


class SandboxType(str, Enum):
    """Types of sandbox environments"""
    LOCAL = "local"          # Local subprocess
    DOCKER = "docker"        # Docker container
    E2B = "e2b"             # E2B cloud sandbox
    VENV = "venv"           # Virtual environment


@dataclass
class SandboxConfig:
    """Configuration for sandbox environment"""
    sandbox_type: SandboxType = SandboxType.LOCAL
    timeout_seconds: int = 300  # 5 minutes default
    memory_limit_mb: int = 1024
    cpu_limit: float = 1.0
    env_variables: Dict[str, str] = field(default_factory=dict)
    python_version: str = "3.11"
    auto_install_deps: bool = True


@dataclass
class ExecutionResult:
    """Result of sandbox execution"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    files_created: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentSandbox:
    """
    Sandbox environment for running generated agent projects.
    
    Provides isolated execution with:
    - Dependency management
    - Resource limits
    - Output capture
    - File system isolation
    """
    
    def __init__(self, config: SandboxConfig = None):
        """
        Initialize the sandbox.
        
        Args:
            config: Sandbox configuration
        """
        self.config = config or SandboxConfig()
        self.sandbox_dir: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self._output_queue = queue.Queue()
        self._logs: List[Dict[str, Any]] = []
    
    def create(self, project_files: Dict[str, str] = None) -> str:
        """
        Create a new sandbox environment.
        
        Args:
            project_files: Dictionary of file_path -> content
            
        Returns:
            Path to the sandbox directory
        """
        # Create temporary directory for sandbox
        self.sandbox_dir = tempfile.mkdtemp(prefix="aegis_sandbox_")
        
        logger.info(f"Created sandbox at: {self.sandbox_dir}")
        
        # Write project files if provided
        if project_files:
            for file_path, content in project_files.items():
                full_path = os.path.join(self.sandbox_dir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        
        # Set up virtual environment if using venv type
        if self.config.sandbox_type == SandboxType.VENV:
            self._setup_venv()
        
        return self.sandbox_dir
    
    def _setup_venv(self):
        """Set up a virtual environment in the sandbox"""
        venv_path = os.path.join(self.sandbox_dir, ".venv")
        
        # Create venv
        subprocess.run(
            [sys.executable, "-m", "venv", venv_path],
            check=True,
            capture_output=True
        )
        
        logger.info(f"Created virtual environment at: {venv_path}")
    
    def install_dependencies(self, requirements: List[str] = None, requirements_file: str = None) -> ExecutionResult:
        """
        Install dependencies in the sandbox.
        
        Args:
            requirements: List of pip packages
            requirements_file: Path to requirements.txt
            
        Returns:
            ExecutionResult with installation output
        """
        if not self.sandbox_dir:
            return ExecutionResult(success=False, error="Sandbox not created")
        
        # Determine pip path
        if self.config.sandbox_type == SandboxType.VENV:
            pip_path = os.path.join(self.sandbox_dir, ".venv", "bin", "pip")
        else:
            pip_path = "pip"
        
        # Build install command
        if requirements_file:
            req_path = os.path.join(self.sandbox_dir, requirements_file)
            if os.path.exists(req_path):
                cmd = [pip_path, "install", "-r", req_path]
            else:
                return ExecutionResult(success=False, error=f"Requirements file not found: {requirements_file}")
        elif requirements:
            cmd = [pip_path, "install"] + requirements
        else:
            # Look for requirements.txt in sandbox
            req_path = os.path.join(self.sandbox_dir, "requirements.txt")
            if os.path.exists(req_path):
                cmd = [pip_path, "install", "-r", req_path]
            else:
                return ExecutionResult(success=True, stdout="No dependencies to install")
        
        logger.info(f"Installing dependencies: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.sandbox_dir,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds
            )
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(success=False, error="Dependency installation timed out")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def run(
        self,
        command: str = None,
        script: str = None,
        task: str = None,
        interactive: bool = False,
        env_override: Dict[str, str] = None,
        on_output: Callable[[str], None] = None
    ) -> ExecutionResult:
        """
        Run a command or script in the sandbox.
        
        Args:
            command: Shell command to run
            script: Python script path to run
            task: Task to pass to main.py
            interactive: Run in interactive mode
            env_override: Override environment variables
            on_output: Callback for real-time output
            
        Returns:
            ExecutionResult with output
        """
        if not self.sandbox_dir:
            return ExecutionResult(success=False, error="Sandbox not created")
        
        # Build environment
        env = os.environ.copy()
        env.update(self.config.env_variables)
        if env_override:
            env.update(env_override)
        
        # Add sandbox to PYTHONPATH
        env["PYTHONPATH"] = f"{self.sandbox_dir}:{env.get('PYTHONPATH', '')}"
        
        # Determine python path
        if self.config.sandbox_type == SandboxType.VENV:
            python_path = os.path.join(self.sandbox_dir, ".venv", "bin", "python")
        else:
            python_path = sys.executable
        
        # Build command
        if command:
            cmd = command
            shell = True
        elif script:
            script_path = os.path.join(self.sandbox_dir, script)
            cmd = [python_path, script_path]
            shell = False
        elif task:
            main_path = os.path.join(self.sandbox_dir, "main.py")
            if os.path.exists(main_path):
                if interactive:
                    cmd = [python_path, main_path, "-i"]
                else:
                    cmd = [python_path, main_path, task]
                shell = False
            else:
                return ExecutionResult(success=False, error="main.py not found in sandbox")
        else:
            return ExecutionResult(success=False, error="No command, script, or task specified")
        
        start_time = datetime.now()
        self.is_running = True
        
        try:
            if on_output:
                # Stream output
                result = self._run_with_streaming(cmd, env, shell, on_output)
            else:
                # Capture output
                if shell:
                    result = subprocess.run(
                        cmd,
                        cwd=self.sandbox_dir,
                        env=env,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=self.config.timeout_seconds
                    )
                else:
                    result = subprocess.run(
                        cmd,
                        cwd=self.sandbox_dir,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=self.config.timeout_seconds
                    )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return ExecutionResult(
                    success=result.returncode == 0,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    execution_time=execution_time
                )
                
        except subprocess.TimeoutExpired:
            return ExecutionResult(success=False, error=f"Execution timed out after {self.config.timeout_seconds}s")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
        finally:
            self.is_running = False
    
    def _run_with_streaming(
        self,
        cmd: Any,
        env: Dict[str, str],
        shell: bool,
        on_output: Callable[[str], None]
    ) -> ExecutionResult:
        """Run command with streaming output"""
        
        start_time = datetime.now()
        stdout_lines = []
        stderr_lines = []
        
        if shell:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.sandbox_dir,
                env=env,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.sandbox_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        # Stream stdout
        def stream_output(pipe, lines, prefix=""):
            for line in iter(pipe.readline, ''):
                lines.append(line)
                on_output(prefix + line)
                self._logs.append({
                    "time": datetime.now().isoformat(),
                    "type": "stdout" if not prefix else "stderr",
                    "content": line.rstrip()
                })
        
        # Start threads to read output
        stdout_thread = threading.Thread(target=stream_output, args=(self.process.stdout, stdout_lines))
        stderr_thread = threading.Thread(target=stream_output, args=(self.process.stderr, stderr_lines, "[STDERR] "))
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process
        try:
            self.process.wait(timeout=self.config.timeout_seconds)
        except subprocess.TimeoutExpired:
            self.process.kill()
            return ExecutionResult(success=False, error="Execution timed out")
        
        stdout_thread.join()
        stderr_thread.join()
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return ExecutionResult(
            success=self.process.returncode == 0,
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
            exit_code=self.process.returncode,
            execution_time=execution_time
        )
    
    def write_file(self, path: str, content: str) -> bool:
        """
        Write a file in the sandbox.
        
        Args:
            path: Relative path in sandbox
            content: File content
            
        Returns:
            Success status
        """
        if not self.sandbox_dir:
            return False
        
        full_path = os.path.join(self.sandbox_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    
    def read_file(self, path: str) -> Optional[str]:
        """
        Read a file from the sandbox.
        
        Args:
            path: Relative path in sandbox
            
        Returns:
            File content or None
        """
        if not self.sandbox_dir:
            return None
        
        full_path = os.path.join(self.sandbox_dir, path)
        
        if not os.path.exists(full_path):
            return None
        
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def list_files(self, path: str = "") -> List[str]:
        """
        List files in the sandbox.
        
        Args:
            path: Relative path to list
            
        Returns:
            List of file paths
        """
        if not self.sandbox_dir:
            return []
        
        full_path = os.path.join(self.sandbox_dir, path)
        
        if not os.path.exists(full_path):
            return []
        
        files = []
        for root, dirs, filenames in os.walk(full_path):
            # Skip hidden directories and venv
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for filename in filenames:
                if not filename.startswith('.'):
                    rel_path = os.path.relpath(os.path.join(root, filename), self.sandbox_dir)
                    files.append(rel_path)
        
        return files
    
    def get_all_files(self) -> Dict[str, str]:
        """
        Get all files and their contents from the sandbox.
        
        Returns:
            Dictionary of path -> content
        """
        files = {}
        for file_path in self.list_files():
            content = self.read_file(file_path)
            if content is not None:
                files[file_path] = content
        return files
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get execution logs"""
        return self._logs.copy()
    
    def stop(self):
        """Stop any running process in the sandbox"""
        if self.process and self.is_running:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.is_running = False
    
    def cleanup(self):
        """Clean up the sandbox"""
        self.stop()
        
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            logger.info(f"Cleaned up sandbox: {self.sandbox_dir}")
            self.sandbox_dir = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


class E2BSandbox(AgentSandbox):
    """
    E2B Cloud Sandbox for agent execution.
    
    Uses E2B's code interpreter for cloud-based isolated execution.
    Requires E2B_API_KEY environment variable.
    """
    
    def __init__(self, config: SandboxConfig = None):
        super().__init__(config)
        self.config.sandbox_type = SandboxType.E2B
        self._e2b_sandbox = None
        self._sandbox_url = None
    
    def create(self, project_files: Dict[str, str] = None) -> str:
        """Create an E2B cloud sandbox"""
        try:
            from e2b_code_interpreter import Sandbox
        except ImportError:
            raise ImportError("e2b_code_interpreter not installed. Run: pip install e2b-code-interpreter")
        
        api_key = os.getenv("E2B_API_KEY")
        if not api_key:
            raise ValueError("E2B_API_KEY environment variable not set")
        
        logger.info("Creating E2B sandbox...")
        
        # Create E2B sandbox (new SDK requires create())
        self._e2b_sandbox = Sandbox.create(
            api_key=api_key,
            timeout=self.config.timeout_seconds,
        )
        
        # Write project files
        if project_files:
            for file_path, content in project_files.items():
                self._write_e2b_file(file_path, content)
        
        # Get sandbox URL
        sandbox_id = getattr(self._e2b_sandbox, 'sandbox_id', 'e2b_sandbox')
        self._sandbox_url = f"https://{sandbox_id}.e2b.app"
        
        logger.info(f"E2B sandbox created: {self._sandbox_url}")
        
        return self._sandbox_url
    
    def _write_e2b_file(self, path: str, content: str):
        """Write a file to the E2B sandbox"""
        if self._e2b_sandbox:
            # Use Python to write the file
            escaped_content = content.replace('"""', '\\"\\"\\"').replace('\\', '\\\\')
            self._e2b_sandbox.run_code(f'''
import os
os.makedirs(os.path.dirname("{path}") or ".", exist_ok=True)
with open("{path}", 'w') as f:
    f.write("""{escaped_content}""")
            ''')
    
    def run(
        self,
        command: str = None,
        script: str = None,
        task: str = None,
        interactive: bool = False,
        env_override: Dict[str, str] = None,
        on_output: Callable[[str], None] = None
    ) -> ExecutionResult:
        """Run code in the E2B sandbox"""
        if not self._e2b_sandbox:
            return ExecutionResult(success=False, error="E2B sandbox not created")
        
        # Build the code to run
        if command:
            code = f'''
import subprocess
result = subprocess.run({repr(command)}, shell=True, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
'''
        elif script:
            code = f'''
exec(open("{script}").read())
'''
        elif task:
            code = f'''
import sys
sys.argv = ["main.py", {repr(task)}]
exec(open("main.py").read())
'''
        else:
            return ExecutionResult(success=False, error="No command, script, or task specified")
        
        start_time = datetime.now()
        
        try:
            result = self._e2b_sandbox.run_code(code)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            stdout = ""
            stderr = ""
            
            if hasattr(result, 'logs'):
                stdout = "\n".join(result.logs.stdout) if result.logs.stdout else ""
                stderr = "\n".join(result.logs.stderr) if result.logs.stderr else ""
            
            if on_output and stdout:
                on_output(stdout)
            
            return ExecutionResult(
                success=not result.error,
                stdout=stdout,
                stderr=stderr,
                error=str(result.error) if result.error else None,
                execution_time=execution_time
            )
            
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def install_dependencies(self, requirements: List[str] = None, requirements_file: str = None) -> ExecutionResult:
        """Install dependencies in E2B sandbox"""
        if not self._e2b_sandbox:
            return ExecutionResult(success=False, error="E2B sandbox not created")
        
        if requirements:
            packages = " ".join(requirements)
        elif requirements_file:
            packages = f"-r {requirements_file}"
        else:
            packages = "-r requirements.txt"
        
        code = f'''
import subprocess
result = subprocess.run(f"pip install {packages}", shell=True, capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("ERROR:", result.stderr)
'''
        
        try:
            result = self._e2b_sandbox.run_code(code)
            stdout = "\n".join(result.logs.stdout) if result.logs.stdout else ""
            stderr = "\n".join(result.logs.stderr) if result.logs.stderr else ""
            
            return ExecutionResult(
                success=not result.error,
                stdout=stdout,
                stderr=stderr
            )
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def cleanup(self):
        """Clean up E2B sandbox"""
        if self._e2b_sandbox:
            try:
                self._e2b_sandbox.kill()
            except:
                pass
            self._e2b_sandbox = None
        super().cleanup()


def create_sandbox(
    sandbox_type: SandboxType = SandboxType.LOCAL,
    config: SandboxConfig = None
) -> AgentSandbox:
    """
    Factory function to create the appropriate sandbox type.
    
    Args:
        sandbox_type: Type of sandbox to create
        config: Sandbox configuration
        
    Returns:
        AgentSandbox instance
    """
    if config is None:
        config = SandboxConfig(sandbox_type=sandbox_type)
    
    if sandbox_type == SandboxType.E2B:
        return E2BSandbox(config)
    else:
        return AgentSandbox(config)
