"""
Tool Registry Service - Dynamic tool discovery and registration
"""

import inspect
import importlib
import pkgutil
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories"""
    FILE = "file"
    WEB = "web"
    CODE = "code"
    TERMINAL = "terminal"
    AUTONOMOUS = "autonomous"
    KNOWLEDGE = "knowledge"
    STORE = "store"
    META = "meta"
    CUSTOM = "custom"
    MCP = "mcp"


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    type: str
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """Tool definition with metadata"""
    name: str
    description: str
    category: ToolCategory
    function: Optional[Callable] = None
    parameters: List[ToolParameter] = field(default_factory=list)
    return_type: str = "any"
    is_async: bool = False
    is_enabled: bool = True
    source: str = "builtin"  # builtin, custom, mcp
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    Central registry for all available tools.
    Supports dynamic discovery and runtime registration.
    """
    
    _instance = None
    
    # Tool name aliases for common mistakes
    TOOL_ALIASES = {
        "search": "search_web",
        "web_search": "search_web",
        "google": "search_web",
        "duckduckgo": "search_web",
        "fetch": "fetch_url",
        "get_url": "fetch_url",
        "scrape": "fetch_and_extract",
        "scrape_url": "fetch_and_extract",
        "extract": "fetch_and_extract",
        "run_python": "execute_python",
        "python": "execute_python",
        "shell": "execute_command",
        "bash": "execute_command",
        "terminal": "run_command",
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}
        self._initialized = True
        self._discover_builtin_tools()
    
    def _discover_builtin_tools(self):
        """Discover and register all built-in tools"""
        # File tools
        self._register_file_tools()
        # Web tools
        self._register_web_tools()
        # Code tools
        self._register_code_tools()
        # Terminal tools
        self._register_terminal_tools()
        # Autonomous tools
        self._register_autonomous_tools()
        # Knowledge tools
        self._register_knowledge_tools()
        # Registry-backed tools (full Aegis toolset)
        self._register_registry_tools()

    def _map_type(self, annotation, default: str = "string") -> str:
        """Best-effort mapping of type hints to JSON-friendly strings"""
        if annotation in (inspect._empty, None):
            return default
        origin = getattr(annotation, "__origin__", None)
        if origin in (list, List):
            return "array"
        if origin in (dict, Dict):
            return "object"
        if origin is bool or annotation is bool:
            return "boolean"
        if origin in (int, float) or annotation in (int, float):
            return "number"
        if annotation is str:
            return "string"
        return default

    def _infer_category(self, func: Callable) -> ToolCategory:
        """Infer a tool category from its module path"""
        module = (getattr(func, "__module__", "") or "").lower()
        if "web" in module:
            return ToolCategory.WEB
        if "file" in module:
            return ToolCategory.FILE
        if "terminal" in module:
            return ToolCategory.TERMINAL
        if "code" in module or "script" in module:
            return ToolCategory.CODE
        if "autonomous" in module or "planning" in module or "escalation" in module:
            return ToolCategory.AUTONOMOUS
        if "knowledge" in module or "connector" in module:
            return ToolCategory.KNOWLEDGE
        if "store" in module:
            return ToolCategory.STORE
        if "meta" in module:
            return ToolCategory.META
        return ToolCategory.CODE

    def _register_registry_tools(self):
        """
        Register all tools declared via the Aegis registry decorators.
        This pulls in the full reference toolset (web/search, store/meta CRUD, etc).
        """
        try:
            import src.aegis.tools as tools_pkg
            from aegis.registry import registry
        except ImportError:
            return

        # Ensure all tool modules are imported so decorator registration runs
        try:
            for _, modname, _ in pkgutil.walk_packages(
                tools_pkg.__path__, tools_pkg.__name__ + "."
            ):
                # Skip private modules
                if ".__" in modname or "._" in modname.split(".")[-1]:
                    continue
                try:
                    importlib.import_module(modname)
                except Exception:
                    # Don't let a single module failure block the rest
                    continue
        except Exception:
            pass

        registry_tools = getattr(registry, "tools", {}) or {}
        registry_info = getattr(registry, "tools_info", {}) or {}

        for func_name, func in registry_tools.items():
            try:
                sig = inspect.signature(func)
            except (TypeError, ValueError):
                continue

            info = registry_info.get(func_name) or registry_info.get(getattr(func, "__name__", func_name))
            description = ""
            if info and info.docstring:
                description = info.docstring.strip().split("\n")[0]
            if not description:
                description = (getattr(func, "__doc__", "") or "").strip().split("\n")[0] or func_name

            parameters = []
            for pname, param in sig.parameters.items():
                if pname == "context_variables":
                    continue
                param_type = self._map_type(param.annotation)
                required = param.default is inspect._empty
                default = None if required else param.default
                parameters.append(
                    ToolParameter(
                        name=pname,
                        type=param_type,
                        description="",
                        required=required,
                        default=default,
                    )
                )

            return_type = self._map_type(sig.return_annotation, default="any")

            self.register(
                ToolDefinition(
                    name=getattr(func, "__name__", func_name),
                    description=description,
                    category=self._infer_category(func),
                    function=func,
                    parameters=parameters,
                    return_type=return_type,
                    is_async=inspect.iscoroutinefunction(func),
                    source="builtin",
                    metadata={
                        "module": getattr(func, "__module__", ""),
                        "from_registry": True,
                    },
                )
            )
    
    def _register_file_tools(self):
        """Register file operation tools"""
        try:
            from src.aegis.tools import file_tools
            
            tools = [
                ToolDefinition(
                    name="read_file",
                    description="Read contents of a file from the workspace",
                    category=ToolCategory.FILE,
                    function=file_tools.read_file,
                    parameters=[
                        ToolParameter("file_path", "string", "Path to the file to read")
                    ],
                    return_type="string"
                ),
                ToolDefinition(
                    name="write_file",
                    description="Write content to a file in the workspace",
                    category=ToolCategory.FILE,
                    function=file_tools.write_file,
                    parameters=[
                        ToolParameter("file_path", "string", "Path to the file to write"),
                        ToolParameter("content", "string", "Content to write to the file")
                    ],
                    return_type="string"
                ),
                ToolDefinition(
                    name="list_files",
                    description="List files in a directory",
                    category=ToolCategory.FILE,
                    function=file_tools.list_files,
                    parameters=[
                        ToolParameter("directory", "string", "Directory path to list", default="."),
                        ToolParameter("recursive", "boolean", "Whether to list recursively", required=False, default=False)
                    ],
                    return_type="array"
                ),
                ToolDefinition(
                    name="search_files",
                    description="Search for files matching a pattern",
                    category=ToolCategory.FILE,
                    function=file_tools.search_files,
                    parameters=[
                        ToolParameter("pattern", "string", "File pattern to search for"),
                        ToolParameter("directory", "string", "Directory to search in", default=".")
                    ],
                    return_type="array"
                ),
            ]
            
            for tool in tools:
                self.register(tool)
        except ImportError:
            pass
    
    def _register_web_tools(self):
        """Register web operation tools"""
        try:
            from src.aegis.tools import web_tools
            
            tools = [
                ToolDefinition(
                    name="fetch_url",
                    description="Fetch content from a URL",
                    category=ToolCategory.WEB,
                    function=web_tools.fetch_url,
                    parameters=[
                        ToolParameter("url", "string", "URL to fetch")
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="search_web",
                    description="Search the web using DuckDuckGo",
                    category=ToolCategory.WEB,
                    function=web_tools.search_web,
                    parameters=[
                        ToolParameter("query", "string", "Search query"),
                        ToolParameter("num_results", "integer", "Number of results", required=False, default=5)
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="extract_content",
                    description="Extract main content from HTML",
                    category=ToolCategory.WEB,
                    function=web_tools.extract_content,
                    parameters=[
                        ToolParameter("html", "string", "HTML content to extract from")
                    ],
                    return_type="string"
                ),
                ToolDefinition(
                    name="fetch_and_extract",
                    description="Fetch URL and extract main content",
                    category=ToolCategory.WEB,
                    function=web_tools.fetch_and_extract,
                    parameters=[
                        ToolParameter("url", "string", "URL to fetch and extract")
                    ],
                    return_type="object"
                ),
            ]
            
            for tool in tools:
                self.register(tool)
        except ImportError:
            pass
    
    def _register_code_tools(self):
        """Register code execution tools"""
        try:
            from src.aegis.tools import code_tools
            
            tools = [
                ToolDefinition(
                    name="execute_python",
                    description="Execute Python code in an isolated environment",
                    category=ToolCategory.CODE,
                    function=code_tools.execute_python,
                    parameters=[
                        ToolParameter("code", "string", "Python code to execute")
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="execute_command",
                    description="Execute a shell command",
                    category=ToolCategory.CODE,
                    function=code_tools.execute_command,
                    parameters=[
                        ToolParameter("command", "string", "Shell command to execute")
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="run_script",
                    description="Run a script file",
                    category=ToolCategory.CODE,
                    function=code_tools.run_script,
                    parameters=[
                        ToolParameter("script_path", "string", "Path to the script file")
                    ],
                    return_type="object"
                ),
            ]
            
            for tool in tools:
                self.register(tool)
        except ImportError:
            pass
    
    def _register_terminal_tools(self):
        """Register terminal tools"""
        try:
            from src.aegis.tools import terminal_tools
            
            tools = [
                ToolDefinition(
                    name="run_command",
                    description="Run a command in the terminal",
                    category=ToolCategory.TERMINAL,
                    function=terminal_tools.run_command,
                    parameters=[
                        ToolParameter("command", "string", "Command to run"),
                        ToolParameter("cwd", "string", "Working directory", required=False)
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="list_directory",
                    description="List contents of a directory",
                    category=ToolCategory.TERMINAL,
                    function=terminal_tools.list_directory,
                    parameters=[
                        ToolParameter("path", "string", "Directory path", default=".")
                    ],
                    return_type="array"
                ),
            ]
            
            for tool in tools:
                self.register(tool)
        except ImportError:
            pass
    
    def _register_autonomous_tools(self):
        """Register autonomous planning tools"""
        try:
            from src.aegis.tools import autonomous
            
            # Task planning tools
            tools = [
                ToolDefinition(
                    name="create_task_plan",
                    description="Create a task plan with subtasks",
                    category=ToolCategory.AUTONOMOUS,
                    function=autonomous.create_task_plan,
                    parameters=[
                        ToolParameter("goal", "string", "Main goal to accomplish"),
                        ToolParameter("subtasks", "array", "List of subtask descriptions", required=False)
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="get_plan_status",
                    description="Get the current status of a task plan",
                    category=ToolCategory.AUTONOMOUS,
                    function=autonomous.get_plan_status,
                    parameters=[
                        ToolParameter("plan_id", "string", "ID of the plan")
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="execute_next_subtask",
                    description="Execute the next pending subtask in a plan",
                    category=ToolCategory.AUTONOMOUS,
                    function=autonomous.execute_next_subtask,
                    parameters=[
                        ToolParameter("plan_id", "string", "ID of the plan")
                    ],
                    return_type="object"
                ),
            ]
            
            for tool in tools:
                self.register(tool)
        except (ImportError, AttributeError):
            pass
    
    def _register_knowledge_tools(self):
        """Register knowledge connector tools"""
        try:
            from src.aegis.tools import knowledge
            
            tools = [
                ToolDefinition(
                    name="search_knowledge",
                    description="Search across connected knowledge sources",
                    category=ToolCategory.KNOWLEDGE,
                    function=knowledge.search_knowledge,
                    parameters=[
                        ToolParameter("query", "string", "Search query"),
                        ToolParameter("connector_ids", "array", "IDs of connectors to search", required=False)
                    ],
                    return_type="object"
                ),
                ToolDefinition(
                    name="query_connector",
                    description="Query a specific knowledge connector",
                    category=ToolCategory.KNOWLEDGE,
                    function=knowledge.query_connector,
                    parameters=[
                        ToolParameter("connector_id", "string", "ID of the connector"),
                        ToolParameter("query", "string", "Query to execute")
                    ],
                    return_type="object"
                ),
            ]
            
            for tool in tools:
                self.register(tool)
        except (ImportError, AttributeError):
            pass
    
    def register(self, tool: ToolDefinition) -> bool:
        """Register a tool in the registry"""
        if tool.name in self._tools:
            # Update existing tool
            self._tools[tool.name] = tool
        else:
            self._tools[tool.name] = tool
            self._categories[tool.category].append(tool.name)
        return True
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool from the registry"""
        if name not in self._tools:
            return False
        
        tool = self._tools[name]
        self._categories[tool.category].remove(name)
        del self._tools[name]
        return True
    
    def resolve_name(self, name: str) -> str:
        """Resolve a tool name, applying aliases if needed"""
        # Check if it's a direct match first
        if name in self._tools:
            return name
        # Check aliases
        if name in self.TOOL_ALIASES:
            aliased = self.TOOL_ALIASES[name]
            if aliased in self._tools:
                return aliased
        return name
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name (with alias resolution)"""
        resolved = self.resolve_name(name)
        return self._tools.get(resolved)
    
    def get_function(self, name: str) -> Optional[Callable]:
        """Get the callable function for a tool (with alias resolution)"""
        resolved = self.resolve_name(name)
        tool = self._tools.get(resolved)
        return tool.function if tool else None
    
    def get_all(self) -> List[ToolDefinition]:
        """Get all registered tools"""
        return list(self._tools.values())
    
    def get_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get tools by category"""
        return [self._tools[name] for name in self._categories.get(category, [])]
    
    def get_by_source(self, source: str) -> List[ToolDefinition]:
        """Get tools by source (builtin, custom, mcp)"""
        return [t for t in self._tools.values() if t.source == source]
    
    def get_enabled(self) -> List[ToolDefinition]:
        """Get all enabled tools"""
        return [t for t in self._tools.values() if t.is_enabled]
    
    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools"""
        return list(self._tools.keys())
    
    def get_tools_for_agent(self, tool_names: List[str]) -> List[Callable]:
        """Get callable functions for specified tool names"""
        functions = []
        for name in tool_names:
            func = self.get_function(name)
            if func:
                functions.append(func)
        return functions
    
    def to_dict(self, name: str) -> Optional[Dict[str, Any]]:
        """Convert a tool to a dictionary representation"""
        tool = self._tools.get(name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category.value,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default
                }
                for p in tool.parameters
            ],
            "return_type": tool.return_type,
            "is_async": tool.is_async,
            "is_enabled": tool.is_enabled,
            "source": tool.source,
            "metadata": tool.metadata
        }
    
    def list_all_as_dict(self) -> List[Dict[str, Any]]:
        """List all tools as dictionaries"""
        return [self.to_dict(name) for name in self._tools.keys()]


# Singleton instance
tool_registry = ToolRegistry()
