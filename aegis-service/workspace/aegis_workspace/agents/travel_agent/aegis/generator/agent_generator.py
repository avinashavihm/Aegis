"""
Agent Generator - AI-powered multi-file agent project generation

"""

import os
import re
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

from litellm import completion
from aegis.generator.project_templates import (
    AgentProjectType,
    ProjectTemplate,
    get_template_for_type,
    BASE_MAIN_TEMPLATE,
    BASE_CONFIG_TEMPLATE,
    BASE_AGENTS_INIT_TEMPLATE,
    BASE_MAIN_AGENT_TEMPLATE,
    BASE_TOOLS_INIT_TEMPLATE,
    BASE_CUSTOM_TOOL_TEMPLATE,
    BASE_UTILS_INIT_TEMPLATE,
    BASE_LOGGER_TEMPLATE,
    BASE_HELPERS_TEMPLATE,
    BASE_REQUIREMENTS_TEMPLATE,
    BASE_ENV_TEMPLATE,
    BASE_README_TEMPLATE,
    MULTI_AGENT_ORCHESTRATOR_TEMPLATE,
    DATA_PIPELINE_TEMPLATE,
)
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


@dataclass
class GeneratedFile:
    """A generated file"""
    path: str
    content: str
    description: str = ""


@dataclass
class GeneratedProject:
    """A complete generated project"""
    name: str
    description: str
    project_type: AgentProjectType
    files: List[GeneratedFile] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_file(self, path: str) -> Optional[GeneratedFile]:
        for f in self.files:
            if f.path == path or f.path.endswith(path):
                return f
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type.value,
            "files": [{"path": f.path, "content": f.content, "description": f.description} for f in self.files],
            "dependencies": self.dependencies,
            "created_at": self.created_at,
            "metadata": self.metadata
        }


SYSTEM_PROMPT = """You are an expert Python agent developer. You generate sophisticated, production-ready multi-file agent projects.

CRITICAL RULES:
1. Generate COMPLETE files - never truncate or use ellipsis (...)
2. Use proper Python syntax and follow PEP 8 style
3. Include comprehensive error handling
4. Make code production-ready with proper logging
5. Generate ALL required files for a working project

OUTPUT FORMAT:
Use XML tags for each file:
<file path="relative/path/to/file.py">
# Complete file content here
</file>

PROJECT STRUCTURE for agent projects:
- main.py              # Entry point with CLI
- config.py            # Configuration management
- agents/__init__.py   # Agent exports
- agents/main_agent.py # Main agent definition
- agents/*.py          # Additional specialized agents
- tools/__init__.py    # Tool exports
- tools/*.py           # Custom tool implementations
- utils/__init__.py    # Utility exports
- utils/logger.py      # Logging setup
- utils/helpers.py     # Helper functions
- requirements.txt     # Dependencies
- .env.example         # Environment template
- README.md           # Documentation

AGENT DEVELOPMENT RULES:
1. Import from aegis: `from aegis.types import Agent`
2. Use aegis tools: `from aegis.tools import read_file, write_file, execute_python`
3. Always include case_resolved and case_not_resolved for task completion
4. Create dynamic instructions using functions when needed
5. Include proper metadata and versioning
6. Make tools reusable and well-documented

TOOL CREATION:
```python
from aegis.registry import register_tool

@register_tool("tool_name")
def tool_name(param1: str, param2: int = 10, context_variables: dict = None) -> str:
    \"\"\"Tool description\"\"\"
    # Implementation
    return result
```

Remember: Generate COMPLETE, PRODUCTION-READY code. No placeholders, no TODOs left unfilled."""


class AgentGenerator:
    """
    AI-powered multi-file agent project generator.
    
    Generates sophisticated agent projects with multiple interconnected files.
    """
    
    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize the generator.
        
        Args:
            model: LLM model to use for generation
        """
        self.model = model
        self.generated_projects: Dict[str, GeneratedProject] = {}
    
    def generate(
        self,
        description: str,
        project_name: str = None,
        project_type: AgentProjectType = AgentProjectType.SIMPLE,
        tools: List[str] = None,
        capabilities: List[str] = None,
        custom_requirements: List[str] = None,
        model_override: str = None,
        stream_callback: Callable[[str, Any], None] = None
    ) -> GeneratedProject:
        """
        Generate a complete multi-file agent project.
        
        Args:
            description: Description of what the agent should do
            project_name: Name for the project (auto-generated if not provided)
            project_type: Type of project to generate
            tools: Specific tools the agent should use
            capabilities: Capabilities the agent should have
            custom_requirements: Additional pip requirements
            model_override: Override the default model
            stream_callback: Callback for streaming progress updates
            
        Returns:
            GeneratedProject with all files
        """
        model = model_override or self.model
        
        # Generate project name if not provided
        if not project_name:
            project_name = self._generate_project_name(description)
        
        # Sanitize project name
        project_name = self._sanitize_name(project_name)
        
        if stream_callback:
            stream_callback("status", {"message": f"Generating project: {project_name}..."})
        
        # Get base template
        template = get_template_for_type(project_type)
        
        # Build the generation prompt
        prompt = self._build_generation_prompt(
            description=description,
            project_name=project_name,
            project_type=project_type,
            template=template,
            tools=tools,
            capabilities=capabilities
        )
        
        if stream_callback:
            stream_callback("status", {"message": "Calling AI to generate code..."})
        
        # Generate code using LLM
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=16000,
            temperature=0.7
        )
        
        generated_code = response.choices[0].message.content
        
        if stream_callback:
            stream_callback("status", {"message": "Parsing generated files..."})
        
        # Parse the generated code into files
        files = self._parse_generated_code(generated_code, project_name)
        
        # Ensure all essential files exist
        files = self._ensure_essential_files(
            files=files,
            project_name=project_name,
            description=description,
            project_type=project_type,
            tools=tools
        )
        
        # Calculate dependencies
        dependencies = list(set(template.dependencies + (custom_requirements or [])))
        
        # Create the project
        project = GeneratedProject(
            name=project_name,
            description=description,
            project_type=project_type,
            files=files,
            dependencies=dependencies,
            metadata={
                "model_used": model,
                "tools": tools,
                "capabilities": capabilities
            }
        )
        
        # Store the project
        self.generated_projects[project_name] = project
        
        if stream_callback:
            stream_callback("complete", {
                "project_name": project_name,
                "files_count": len(files),
                "files": [f.path for f in files]
            })
        
        logger.info(f"Generated project '{project_name}' with {len(files)} files")
        
        return project
    
    def generate_streaming(
        self,
        description: str,
        project_name: str = None,
        project_type: AgentProjectType = AgentProjectType.SIMPLE,
        tools: List[str] = None,
        capabilities: List[str] = None,
        model_override: str = None
    ):
        """
        Generate project with streaming output.
        
        Yields progress updates and generated files as they're created.
        """
        model = model_override or self.model
        
        if not project_name:
            project_name = self._generate_project_name(description)
        
        project_name = self._sanitize_name(project_name)
        
        yield {"type": "status", "message": f"Starting generation for: {project_name}"}
        
        template = get_template_for_type(project_type)
        
        prompt = self._build_generation_prompt(
            description=description,
            project_name=project_name,
            project_type=project_type,
            template=template,
            tools=tools,
            capabilities=capabilities
        )
        
        yield {"type": "status", "message": "Generating code..."}
        
        # Stream the LLM response
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=16000,
            temperature=0.7,
            stream=True
        )
        
        full_response = ""
        current_file = ""
        current_path = ""
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                current_file += text
                
                yield {"type": "stream", "text": text}
                
                # Check for file boundaries
                if '<file path="' in text:
                    match = re.search(r'<file path="([^"]+)"', text)
                    if match:
                        current_path = match.group(1)
                        yield {"type": "file_start", "path": current_path}
                
                if '</file>' in current_file and current_path:
                    yield {"type": "file_complete", "path": current_path}
                    current_file = ""
                    current_path = ""
        
        # Parse all files
        files = self._parse_generated_code(full_response, project_name)
        files = self._ensure_essential_files(
            files=files,
            project_name=project_name,
            description=description,
            project_type=project_type,
            tools=tools
        )
        
        project = GeneratedProject(
            name=project_name,
            description=description,
            project_type=project_type,
            files=files,
            dependencies=template.dependencies
        )
        
        self.generated_projects[project_name] = project
        
        yield {
            "type": "complete",
            "project": project.to_dict()
        }
    
    def _build_generation_prompt(
        self,
        description: str,
        project_name: str,
        project_type: AgentProjectType,
        template: ProjectTemplate,
        tools: List[str] = None,
        capabilities: List[str] = None
    ) -> str:
        """Build the prompt for code generation"""
        
        tools_str = ""
        if tools:
            tools_str = f"""
REQUIRED TOOLS:
The agent MUST use these aegis tools:
{chr(10).join(f'- {t}' for t in tools)}

Import them from aegis.tools:
from aegis.tools import {', '.join(tools)}
"""
        
        capabilities_str = ""
        if capabilities:
            capabilities_str = f"""
REQUIRED CAPABILITIES:
The agent must have these capabilities:
{chr(10).join(f'- {c}' for c in capabilities)}
"""
        
        type_specific = ""
        if project_type == AgentProjectType.MULTI_AGENT:
            type_specific = """
MULTI-AGENT SYSTEM REQUIREMENTS:
1. Create multiple specialized agents in agents/ folder
2. Include an orchestrator that routes tasks to appropriate agents
3. Implement agent coordination and context sharing
4. Each agent should have clear responsibilities
"""
        elif project_type == AgentProjectType.DATA_PIPELINE:
            type_specific = """
DATA PIPELINE REQUIREMENTS:
1. Include data extraction, transformation, and loading stages
2. Create pipeline configuration in config
3. Support for multiple data formats (JSON, CSV, etc.)
4. Include data validation tools
"""
        elif project_type == AgentProjectType.WEB_AUTOMATION:
            type_specific = """
WEB AUTOMATION REQUIREMENTS:
1. Include web scraping tools with rate limiting
2. Support for multiple output formats
3. Error handling for network issues
4. Respect robots.txt and rate limits
"""
        elif project_type == AgentProjectType.API_INTEGRATION:
            type_specific = """
API INTEGRATION REQUIREMENTS:
1. Include HTTP client utilities
2. Support for authentication (API keys, OAuth)
3. Rate limiting and retry logic
4. Response parsing and validation
"""
        
        return f"""Generate a complete, production-ready Python agent project.

PROJECT DETAILS:
- Name: {project_name}
- Type: {project_type.value}
- Description: {description}

{tools_str}
{capabilities_str}
{type_specific}

REQUIRED FILES (generate ALL of these):
1. main.py - Entry point with CLI support
2. config.py - Configuration management
3. agents/__init__.py - Agent exports
4. agents/main_agent.py - Main agent with clear instructions
5. tools/__init__.py - Custom tool exports
6. tools/custom_tools.py - At least 2-3 custom tools specific to this agent
7. utils/__init__.py - Utility exports
8. utils/logger.py - Logging setup
9. utils/helpers.py - Helper functions
10. requirements.txt - All dependencies
11. .env.example - Environment template
12. README.md - Comprehensive documentation

GENERATE COMPLETE FILES. Use <file path="...">content</file> format.

The agent should be sophisticated and production-ready, not a basic template.
Include real implementation logic, not just placeholders."""
    
    def _parse_generated_code(self, code: str, project_name: str) -> List[GeneratedFile]:
        """Parse AI-generated code into file objects"""
        files = []
        
        # Find all file blocks
        file_pattern = r'<file path="([^"]+)">([\s\S]*?)(?:</file>|$)'
        matches = re.finditer(file_pattern, code)
        
        for match in matches:
            path = match.group(1).strip()
            content = match.group(2).strip()
            
            # Ensure path is relative to project
            if not path.startswith(project_name):
                path = f"{project_name}/{path}"
            
            # Clean up content
            content = self._clean_code_content(content)
            
            files.append(GeneratedFile(
                path=path,
                content=content,
                description=f"Generated file: {path}"
            ))
        
        return files
    
    def _clean_code_content(self, content: str) -> str:
        """Clean up generated code content"""
        # Remove any markdown code blocks that might have been included
        content = re.sub(r'^```python\n', '', content)
        content = re.sub(r'^```\n', '', content)
        content = re.sub(r'\n```$', '', content)
        
        return content.strip()
    
    def _ensure_essential_files(
        self,
        files: List[GeneratedFile],
        project_name: str,
        description: str,
        project_type: AgentProjectType,
        tools: List[str] = None
    ) -> List[GeneratedFile]:
        """Ensure all essential files exist"""
        
        essential_files = {
            f"{project_name}/main.py": lambda: self._generate_main_file(project_name, description),
            f"{project_name}/config.py": lambda: self._generate_config_file(project_name),
            f"{project_name}/agents/__init__.py": lambda: self._generate_agents_init(project_name),
            f"{project_name}/agents/main_agent.py": lambda: self._generate_main_agent(project_name, description, tools),
            f"{project_name}/tools/__init__.py": lambda: self._generate_tools_init(project_name),
            f"{project_name}/utils/__init__.py": lambda: BASE_UTILS_INIT_TEMPLATE.format(project_name=project_name),
            f"{project_name}/utils/logger.py": lambda: BASE_LOGGER_TEMPLATE.format(project_name=project_name),
            f"{project_name}/utils/helpers.py": lambda: BASE_HELPERS_TEMPLATE.format(project_name=project_name, additional_helpers=""),
            f"{project_name}/requirements.txt": lambda: self._generate_requirements(project_name, project_type),
            f"{project_name}/.env.example": lambda: BASE_ENV_TEMPLATE.format(
                project_name=project_name,
                default_model="gpt-4o",
                additional_env=""
            ),
            f"{project_name}/README.md": lambda: self._generate_readme(project_name, description, tools),
        }
        
        existing_paths = {f.path for f in files}
        
        for path, generator in essential_files.items():
            # Check if file exists (with or without project name prefix)
            if path not in existing_paths and path.replace(f"{project_name}/", "") not in existing_paths:
                files.append(GeneratedFile(
                    path=path,
                    content=generator(),
                    description=f"Essential file: {path}"
                ))
        
        return files
    
    def _generate_main_file(self, project_name: str, description: str) -> str:
        return BASE_MAIN_TEMPLATE.format(
            project_name=project_name,
            project_description=description
        )
    
    def _generate_config_file(self, project_name: str) -> str:
        return BASE_CONFIG_TEMPLATE.format(
            project_name=project_name,
            default_model="gpt-4o",
            custom_config="    pass"
        )
    
    def _generate_agents_init(self, project_name: str) -> str:
        return BASE_AGENTS_INIT_TEMPLATE.format(
            project_name=project_name,
            additional_imports="",
            additional_exports=""
        )
    
    def _generate_main_agent(self, project_name: str, description: str, tools: List[str] = None) -> str:
        tool_imports = ""
        tool_list = ""
        
        if tools:
            tool_imports = f"from aegis.tools import {', '.join(tools)}"
            tool_list = "\n".join(f"        {t}," for t in tools)
        
        return BASE_MAIN_AGENT_TEMPLATE.format(
            project_name=project_name,
            agent_name=project_name.replace("_", " ").title(),
            agent_description=description,
            instructions=f"You are the {project_name} agent. {description}",
            tool_imports=tool_imports,
            tool_list=tool_list,
            parallel_tools="False"
        )
    
    def _generate_tools_init(self, project_name: str) -> str:
        return BASE_TOOLS_INIT_TEMPLATE.format(
            project_name=project_name,
            tool_imports="# Custom tools will be imported here",
            tool_exports="    # Tool names here"
        )
    
    def _generate_requirements(self, project_name: str, project_type: AgentProjectType) -> str:
        template = get_template_for_type(project_type)
        deps = "\n".join(template.dependencies)
        return BASE_REQUIREMENTS_TEMPLATE.format(
            project_name=project_name,
            additional_deps=deps
        )
    
    def _generate_readme(self, project_name: str, description: str, tools: List[str] = None) -> str:
        tools_list = "- Built-in aegis tools\n"
        if tools:
            tools_list = "\n".join(f"- {t}" for t in tools)
        
        return BASE_README_TEMPLATE.format(
            project_name=project_name,
            project_description=description,
            features_list="- AI-powered agent execution\n- CLI interface\n- Interactive mode",
            tools_list=tools_list
        )
    
    def _generate_project_name(self, description: str) -> str:
        """Generate a project name from description"""
        words = description.lower().split()[:3]
        name = "_".join(w for w in words if w.isalnum())
        return name or "agent_project"
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name"""
        # Remove special characters, keep alphanumeric and underscore
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)
        # Remove leading/trailing underscores
        name = name.strip('_')
        return name.lower() or "agent_project"
    
    def save_project(self, project: GeneratedProject, output_dir: str) -> str:
        """
        Save a generated project to disk.
        
        Args:
            project: The generated project
            output_dir: Directory to save the project
            
        Returns:
            Path to the saved project
        """
        project_dir = os.path.join(output_dir, project.name)
        
        for file in project.files:
            # Get relative path within project
            if file.path.startswith(project.name):
                rel_path = file.path[len(project.name):].lstrip('/')
            else:
                rel_path = file.path
            
            file_path = os.path.join(project_dir, rel_path)
            
            # Create directory if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file.content)
        
        logger.info(f"Saved project to: {project_dir}")
        return project_dir
