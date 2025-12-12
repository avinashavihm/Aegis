"""
Connector Registry for managing knowledge connectors
"""

from typing import Dict, List, Optional, Type, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum


class ConnectorType(str, Enum):
    """Types of connectors"""
    DATABASE = "database"
    API = "api"
    FILE = "file"
    CLOUD = "cloud"
    MESSAGE_QUEUE = "message_queue"
    CUSTOM = "custom"


class ConnectionStatus(str, Enum):
    """Connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ConnectorConfig:
    """Configuration for a connector"""
    connector_id: str
    connector_type: ConnectorType
    name: str
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    credentials: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.
    Defines the interface that all connectors must implement.
    """
    
    connector_type: ConnectorType = ConnectorType.CUSTOM
    name: str = "Base Connector"
    description: str = "Base connector class"
    
    def __init__(self, config: ConnectorConfig):
        """
        Initialize the connector.
        
        Args:
            config: Connector configuration
        """
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self._connection = None
        self.last_error: Optional[str] = None
        self.last_connected: Optional[str] = None
        self.query_count: int = 0
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection.
        
        Returns:
            True if disconnection successful
        """
        pass
    
    @abstractmethod
    def query(self, query: str, params: Dict[str, Any] = None) -> Any:
        """
        Execute a query.
        
        Args:
            query: Query string
            params: Query parameters
            
        Returns:
            Query results
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test the connection.
        
        Returns:
            True if connection is healthy
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get connector status"""
        return {
            "connector_id": self.config.connector_id,
            "name": self.config.name,
            "type": self.connector_type.value,
            "status": self.status.value,
            "last_error": self.last_error,
            "last_connected": self.last_connected,
            "query_count": self.query_count,
            "enabled": self.config.enabled
        }
    
    def _set_connected(self):
        """Mark as connected"""
        self.status = ConnectionStatus.CONNECTED
        self.last_connected = datetime.now().isoformat()
        self.last_error = None
    
    def _set_error(self, error: str):
        """Mark as error"""
        self.status = ConnectionStatus.ERROR
        self.last_error = error


class ConnectorRegistry:
    """
    Registry for connector types and instances.
    """
    
    _connector_types: Dict[str, Type[BaseConnector]] = {}
    _instances: Dict[str, BaseConnector] = {}
    _configs: Dict[str, ConnectorConfig] = {}
    
    @classmethod
    def register_type(cls, connector_class: Type[BaseConnector]):
        """
        Register a connector type.
        
        Args:
            connector_class: The connector class to register
        """
        key = f"{connector_class.connector_type.value}:{connector_class.name}"
        cls._connector_types[key] = connector_class
    
    @classmethod
    def get_connector_type(cls, connector_type: ConnectorType, name: str) -> Optional[Type[BaseConnector]]:
        """Get a registered connector type"""
        key = f"{connector_type.value}:{name}"
        return cls._connector_types.get(key)
    
    @classmethod
    def list_connector_types(cls) -> List[Dict[str, str]]:
        """List all registered connector types"""
        return [
            {
                "key": key,
                "type": cc.connector_type.value,
                "name": cc.name,
                "description": cc.description
            }
            for key, cc in cls._connector_types.items()
        ]
    
    @classmethod
    def create_instance(cls, config: ConnectorConfig) -> Optional[BaseConnector]:
        """
        Create a connector instance from config.
        
        Args:
            config: Connector configuration
            
        Returns:
            Connector instance or None
        """
        # Find matching connector class
        for key, connector_class in cls._connector_types.items():
            if connector_class.connector_type == config.connector_type:
                if connector_class.name == config.name or config.name in key:
                    instance = connector_class(config)
                    cls._instances[config.connector_id] = instance
                    cls._configs[config.connector_id] = config
                    return instance
        
        return None
    
    @classmethod
    def get_instance(cls, connector_id: str) -> Optional[BaseConnector]:
        """Get a connector instance by ID"""
        return cls._instances.get(connector_id)
    
    @classmethod
    def list_instances(cls) -> List[Dict[str, Any]]:
        """List all connector instances"""
        return [
            instance.get_status()
            for instance in cls._instances.values()
        ]
    
    @classmethod
    def remove_instance(cls, connector_id: str) -> bool:
        """
        Remove a connector instance.
        
        Args:
            connector_id: ID of connector to remove
            
        Returns:
            True if removed
        """
        if connector_id in cls._instances:
            instance = cls._instances[connector_id]
            if instance.status == ConnectionStatus.CONNECTED:
                instance.disconnect()
            del cls._instances[connector_id]
            if connector_id in cls._configs:
                del cls._configs[connector_id]
            return True
        return False
    
    @classmethod
    def get_config(cls, connector_id: str) -> Optional[ConnectorConfig]:
        """Get connector configuration"""
        return cls._configs.get(connector_id)

