"""
Aegis Agent Generator - Superior multi-file agent project generation

This module provides:
- AI-powered multi-file agent generation 
- Sandbox execution for running generated agents
- Package export for downloading complete agent projects
"""

from aegis.generator.agent_generator import AgentGenerator
from aegis.generator.agent_sandbox import (
    AgentSandbox,
    SandboxConfig,
    SandboxType,
    create_sandbox,
)
from aegis.generator.agent_packager import AgentPackager
from aegis.generator.project_templates import (
    ProjectTemplate,
    get_template_for_type,
    AGENT_PROJECT_TYPES
)

__all__ = [
    "AgentGenerator",
    "AgentSandbox",
    "SandboxConfig",
    "SandboxType",
    "create_sandbox",
    "AgentPackager",
    "ProjectTemplate",
    "get_template_for_type",
    "AGENT_PROJECT_TYPES",
]
