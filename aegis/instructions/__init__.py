"""
Structured Instructions System for Aegis

Provides tools for building, formatting, and managing agent instructions
with support for templates, output formatting, and instruction composition.
"""

from aegis.instructions.instruction_builder import InstructionBuilder
from aegis.instructions.formatters import OutputFormatter, FormatType
from aegis.instructions.prompt_templates import PromptTemplate, TemplateRegistry

__all__ = [
    "InstructionBuilder",
    "OutputFormatter",
    "FormatType",
    "PromptTemplate",
    "TemplateRegistry"
]

