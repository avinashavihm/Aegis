"""
File operation tools
"""

from aegis.registry import register_tool
from aegis.environment.file_env import FileEnv


@register_tool("read_file")
def read_file(file_path: str, context_variables: dict = None) -> str:
    """
    Read the contents of a file.
    
    Args:
        file_path: Path to the file relative to the workspace root.
    """
    file_env: FileEnv = context_variables.get("file_env") if context_variables else None
    if not file_env:
        file_env = FileEnv()
    return file_env.read_file(file_path)


@register_tool("write_file")
def write_file(file_path: str, content: str, context_variables: dict = None) -> str:
    """
    Write content to a file. Creates the file if it doesn't exist.
    
    Args:
        file_path: Path to the file relative to the workspace root.
        content: Content to write to the file.
    """
    file_env: FileEnv = context_variables.get("file_env") if context_variables else None
    if not file_env:
        file_env = FileEnv()
    return file_env.write_file(file_path, content)


@register_tool("list_files")
def list_files(directory: str = ".", recursive: bool = False, context_variables: dict = None) -> str:
    """
    List files in a directory.
    
    Args:
        directory: Directory to list (relative to workspace root).
        recursive: Whether to list files recursively.
    """
    file_env: FileEnv = context_variables.get("file_env") if context_variables else None
    if not file_env:
        file_env = FileEnv()
    files = file_env.list_files(directory, recursive)
    return "\n".join(files) if files else "No files found."


@register_tool("search_files")
def search_files(pattern: str, directory: str = ".", context_variables: dict = None) -> str:
    """
    Search for files matching a pattern.
    
    Args:
        pattern: File pattern to search for (e.g., "*.py").
        directory: Directory to search in (relative to workspace root).
    """
    file_env: FileEnv = context_variables.get("file_env") if context_variables else None
    if not file_env:
        file_env = FileEnv()
    files = file_env.search_files(pattern, directory)
    return "\n".join(files) if files else f"No files found matching pattern: {pattern}"

