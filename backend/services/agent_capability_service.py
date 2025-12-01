"""Service for managing agent capabilities"""
from typing import Dict, List, Optional, Any
from backend.models import CapabilityType, Agent


class CapabilityRegistry:
    """Registry for agent capabilities"""
    
    # Capability definitions with their supported operations
    CAPABILITY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
        CapabilityType.DATA_PROCESSING.value: {
            "name": "Data Processing",
            "description": "Transform, filter, aggregate, validate, and enrich data",
            "operations": ["transform", "filter", "aggregate", "validate", "enrich"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["transform", "filter", "aggregate", "validate", "enrich"]},
                    "rules": {"type": "object"}
                }
            }
        },
        CapabilityType.API_INTEGRATION.value: {
            "name": "API Integration",
            "description": "HTTP requests, REST/GraphQL, webhooks, OAuth",
            "operations": ["http_request", "rest", "graphql", "webhook", "oauth"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                    "auth_type": {"type": "string", "enum": ["none", "bearer", "oauth", "api_key"]}
                }
            }
        },
        CapabilityType.FILE_OPERATIONS.value: {
            "name": "File Operations",
            "description": "Read/write, format conversion, compression, archiving",
            "operations": ["read", "write", "convert", "compress", "archive"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["read", "write", "convert", "compress", "archive"]},
                    "path": {"type": "string"},
                    "format": {"type": "string"}
                }
            }
        },
        CapabilityType.DATABASE_OPERATIONS.value: {
            "name": "Database Operations",
            "description": "Queries, transactions, migrations, backups",
            "operations": ["query", "transaction", "migrate", "backup"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["query", "transaction", "migrate", "backup"]},
                    "connection_string": {"type": "string"}
                }
            }
        },
        CapabilityType.ML_AI.value: {
            "name": "ML/AI",
            "description": "Predictions, classification, embeddings, NLP, image processing",
            "operations": ["predict", "classify", "embed", "nlp", "image_process"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["predict", "classify", "embed", "nlp", "image_process"]},
                    "model": {"type": "string"}
                }
            }
        },
        CapabilityType.WEB_SCRAPING.value: {
            "name": "Web Scraping",
            "description": "HTML parsing, dynamic content, rate limiting, proxies",
            "operations": ["parse", "scrape", "extract"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "selector": {"type": "string"},
                    "rate_limit": {"type": "number"}
                }
            }
        },
        CapabilityType.COMMUNICATION.value: {
            "name": "Communication",
            "description": "Email, SMS, push notifications, Slack/Discord, Teams",
            "operations": ["email", "sms", "push", "slack", "discord", "teams"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "enum": ["email", "sms", "push", "slack", "discord", "teams"]},
                    "recipient": {"type": "string"}
                }
            }
        },
        CapabilityType.SCHEDULING.value: {
            "name": "Scheduling",
            "description": "Cron, intervals, event-driven, conditional triggers",
            "operations": ["cron", "interval", "event", "conditional"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["cron", "interval", "event", "conditional"]},
                    "schedule": {"type": "string"}
                }
            }
        },
        CapabilityType.MONITORING.value: {
            "name": "Monitoring",
            "description": "Health checks, metrics collection, alerting",
            "operations": ["health_check", "metrics", "alert"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["health_check", "metrics", "alert"]},
                    "threshold": {"type": "number"}
                }
            }
        },
        CapabilityType.SECURITY.value: {
            "name": "Security",
            "description": "Encryption, authentication, authorization, audit logging",
            "operations": ["encrypt", "authenticate", "authorize", "audit"],
            "config_schema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["encrypt", "authenticate", "authorize", "audit"]},
                    "algorithm": {"type": "string"}
                }
            }
        },
        CapabilityType.CUSTOM.value: {
            "name": "Custom",
            "description": "Custom capability with user-defined operations",
            "operations": [],
            "config_schema": {
                "type": "object"
            }
        }
    }
    
    @classmethod
    def get_capability_info(cls, capability_type: str) -> Optional[Dict[str, Any]]:
        """Get information about a capability type"""
        return cls.CAPABILITY_DEFINITIONS.get(capability_type)
    
    @classmethod
    def list_capabilities(cls) -> List[Dict[str, Any]]:
        """List all available capabilities"""
        return [
            {
                "type": cap_type,
                **info
            }
            for cap_type, info in cls.CAPABILITY_DEFINITIONS.items()
        ]
    
    @classmethod
    def validate_capability_config(cls, capability_type: str, config: Dict[str, Any]) -> bool:
        """Validate capability configuration"""
        capability_info = cls.get_capability_info(capability_type)
        if not capability_info:
            return False
        
        # Basic validation - can be enhanced with JSON schema validation
        schema = capability_info.get("config_schema", {})
        if not schema:
            return True
        
        # Check if required properties are present
        required = schema.get("required", [])
        for prop in required:
            if prop not in config:
                return False
        
        return True


def get_agent_capabilities(agent: Agent) -> List[str]:
    """Get list of capability types for an agent"""
    return agent.agent_capabilities or []


def validate_agent_capability_config(agent: Agent) -> bool:
    """Validate agent's capability configuration"""
    if not agent.agent_capabilities:
        return True
    
    for capability_type in agent.agent_capabilities:
        if not CapabilityRegistry.get_capability_info(capability_type):
            return False
        
        if agent.capability_config:
            # Validate config for this capability type
            if not CapabilityRegistry.validate_capability_config(
                capability_type,
                agent.capability_config.get(capability_type, {})
            ):
                return False
    
    return True


def get_default_resource_limits() -> Dict[str, Any]:
    """Get default resource limits for agents"""
    return {
        "cpu": "1",
        "memory": "512Mi",
        "timeout": 300,  # seconds
        "max_retries": 3,
        "retry_backoff": "exponential",
        "retry_jitter": True
    }

