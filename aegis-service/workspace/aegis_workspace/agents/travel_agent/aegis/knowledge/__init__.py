"""
Knowledge Grounding System (Work IQ) for Aegis

Provides external connectors for grounding agents with organizational knowledge.
"""

from aegis.knowledge.connector_manager import ConnectorManager, connector_manager
from aegis.knowledge.connector_registry import ConnectorRegistry

__all__ = [
    "ConnectorManager",
    "connector_manager",
    "ConnectorRegistry"
]

