"""
Agent Store for Aegis

Provides agent templates, versioning, and a store infrastructure
for discovering and installing pre-built agents.
"""

from aegis.store.agent_store import AgentStore, agent_store
from aegis.store.templates import AgentTemplate, TemplateCategory
from aegis.store.store_registry import StoreRegistry

__all__ = [
    "AgentStore",
    "agent_store",
    "AgentTemplate",
    "TemplateCategory",
    "StoreRegistry"
]

