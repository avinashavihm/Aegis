"""
Connector Manager for Knowledge Grounding

Manages multiple connectors and provides a unified interface for knowledge retrieval.
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from aegis.knowledge.connector_registry import (
    ConnectorRegistry, BaseConnector, ConnectorConfig, 
    ConnectorType, ConnectionStatus
)
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


class ConnectorManager:
    """
    Manages knowledge connectors for grounding agents.
    Provides unified interface for querying multiple data sources.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the connector manager.
        
        Args:
            config_path: Path to connector configurations
        """
        self.config_path = config_path
        self.registry = ConnectorRegistry
        self.query_cache: Dict[str, Any] = {}
        self.cache_ttl: int = 300  # 5 minutes
        
        if config_path and os.path.exists(config_path):
            self._load_configs()
    
    def create_connector(self, connector_type: str, name: str, 
                         config: Dict[str, Any], credentials: Dict[str, str] = None,
                         description: str = "") -> Optional[str]:
        """
        Create a new connector.
        
        Args:
            connector_type: Type of connector (database, api, file, cloud)
            name: Name identifier
            config: Connection configuration
            credentials: Authentication credentials
            description: Connector description
            
        Returns:
            Connector ID if successful
        """
        # Map string to ConnectorType
        type_map = {
            "database": ConnectorType.DATABASE,
            "api": ConnectorType.API,
            "file": ConnectorType.FILE,
            "cloud": ConnectorType.CLOUD,
            "message_queue": ConnectorType.MESSAGE_QUEUE,
            "custom": ConnectorType.CUSTOM
        }
        
        conn_type = type_map.get(connector_type.lower(), ConnectorType.CUSTOM)
        connector_id = f"{conn_type.value}-{name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        connector_config = ConnectorConfig(
            connector_id=connector_id,
            connector_type=conn_type,
            name=name,
            description=description,
            config=config,
            credentials=credentials or {}
        )
        
        instance = self.registry.create_instance(connector_config)
        
        if instance:
            logger.info(f"Created connector: {connector_id}", title="ConnectorManager")
            return connector_id
        else:
            logger.warning(f"Failed to create connector: {name}", title="ConnectorManager")
            return None
    
    def connect(self, connector_id: str) -> bool:
        """
        Connect a specific connector.
        
        Args:
            connector_id: ID of connector to connect
            
        Returns:
            True if connection successful
        """
        instance = self.registry.get_instance(connector_id)
        if not instance:
            return False
        
        try:
            result = instance.connect()
            if result:
                logger.info(f"Connected: {connector_id}", title="ConnectorManager")
            return result
        except Exception as e:
            logger.error(f"Connection failed for {connector_id}: {e}", title="ConnectorManager")
            instance._set_error(str(e))
            return False
    
    def disconnect(self, connector_id: str) -> bool:
        """
        Disconnect a specific connector.
        
        Args:
            connector_id: ID of connector to disconnect
            
        Returns:
            True if disconnection successful
        """
        instance = self.registry.get_instance(connector_id)
        if not instance:
            return False
        
        try:
            return instance.disconnect()
        except Exception as e:
            logger.error(f"Disconnection failed for {connector_id}: {e}", title="ConnectorManager")
            return False
    
    def query(self, connector_id: str, query: str, 
              params: Dict[str, Any] = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute a query on a connector.
        
        Args:
            connector_id: ID of connector to query
            query: Query string
            params: Query parameters
            use_cache: Whether to use cache
            
        Returns:
            Query results
        """
        instance = self.registry.get_instance(connector_id)
        if not instance:
            return {"error": f"Connector {connector_id} not found"}
        
        # Check cache
        if use_cache:
            cache_key = f"{connector_id}:{query}:{json.dumps(params or {})}"
            cached = self._get_cached(cache_key)
            if cached:
                return {"result": cached, "from_cache": True}
        
        # Ensure connected
        if instance.status != ConnectionStatus.CONNECTED:
            if not self.connect(connector_id):
                return {"error": "Failed to connect"}
        
        try:
            result = instance.query(query, params)
            instance.query_count += 1
            
            # Cache result
            if use_cache:
                self._set_cached(cache_key, result)
            
            return {"result": result, "from_cache": False}
            
        except Exception as e:
            logger.error(f"Query failed on {connector_id}: {e}", title="ConnectorManager")
            return {"error": str(e)}
    
    def query_all(self, query: str, params: Dict[str, Any] = None,
                  connector_types: List[str] = None) -> Dict[str, Any]:
        """
        Query all connected connectors.
        
        Args:
            query: Query string
            params: Query parameters
            connector_types: Filter by connector types
            
        Returns:
            Combined results from all connectors
        """
        results = {}
        
        for connector_id, instance in self.registry._instances.items():
            # Filter by type if specified
            if connector_types:
                if instance.connector_type.value not in connector_types:
                    continue
            
            # Skip disabled connectors
            if not instance.config.enabled:
                continue
            
            result = self.query(connector_id, query, params)
            results[connector_id] = result
        
        return {
            "query": query,
            "results": results,
            "connector_count": len(results)
        }
    
    def search(self, search_term: str, connector_ids: List[str] = None) -> Dict[str, Any]:
        """
        Search across connectors.
        
        Args:
            search_term: Term to search for
            connector_ids: Optional list of connectors to search
            
        Returns:
            Search results
        """
        results = []
        
        connectors_to_search = connector_ids or list(self.registry._instances.keys())
        
        for connector_id in connectors_to_search:
            instance = self.registry.get_instance(connector_id)
            if not instance or not instance.config.enabled:
                continue
            
            try:
                result = self.query(connector_id, f"search:{search_term}", {})
                if not result.get("error"):
                    results.append({
                        "connector_id": connector_id,
                        "connector_type": instance.connector_type.value,
                        "results": result.get("result", [])
                    })
            except Exception:
                continue
        
        return {
            "search_term": search_term,
            "results": results,
            "total_connectors_searched": len(connectors_to_search)
        }
    
    def get_connector_status(self, connector_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a connector"""
        instance = self.registry.get_instance(connector_id)
        if instance:
            return instance.get_status()
        return None
    
    def list_connectors(self, connector_type: str = None,
                        status: str = None) -> List[Dict[str, Any]]:
        """
        List all connectors with optional filters.
        
        Args:
            connector_type: Filter by type
            status: Filter by status
            
        Returns:
            List of connector statuses
        """
        connectors = self.registry.list_instances()
        
        if connector_type:
            connectors = [c for c in connectors if c["type"] == connector_type]
        
        if status:
            connectors = [c for c in connectors if c["status"] == status]
        
        return connectors
    
    def remove_connector(self, connector_id: str) -> bool:
        """Remove a connector"""
        return self.registry.remove_instance(connector_id)
    
    def test_connector(self, connector_id: str) -> Dict[str, Any]:
        """
        Test a connector's connection.
        
        Args:
            connector_id: ID of connector to test
            
        Returns:
            Test results
        """
        instance = self.registry.get_instance(connector_id)
        if not instance:
            return {"success": False, "error": "Connector not found"}
        
        try:
            result = instance.test_connection()
            return {
                "success": result,
                "connector_id": connector_id,
                "status": instance.status.value
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connector statistics"""
        instances = list(self.registry._instances.values())
        
        by_type = {}
        by_status = {}
        total_queries = 0
        
        for instance in instances:
            t = instance.connector_type.value
            s = instance.status.value
            
            by_type[t] = by_type.get(t, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1
            total_queries += instance.query_count
        
        return {
            "total_connectors": len(instances),
            "by_type": by_type,
            "by_status": by_status,
            "total_queries": total_queries,
            "cache_entries": len(self.query_cache),
            "available_connector_types": [
                ct["key"] for ct in self.registry.list_connector_types()
            ]
        }
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached result"""
        if key in self.query_cache:
            entry = self.query_cache[key]
            age = (datetime.now() - datetime.fromisoformat(entry["timestamp"])).total_seconds()
            if age < self.cache_ttl:
                return entry["data"]
            else:
                del self.query_cache[key]
        return None
    
    def _set_cached(self, key: str, data: Any):
        """Cache a result"""
        self.query_cache[key] = {
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Limit cache size
        if len(self.query_cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self.query_cache.keys(),
                key=lambda k: self.query_cache[k]["timestamp"]
            )
            for k in sorted_keys[:100]:
                del self.query_cache[k]
    
    def clear_cache(self):
        """Clear the query cache"""
        self.query_cache = {}
    
    def _load_configs(self):
        """Load connector configurations from file"""
        if not self.config_path:
            return
        
        try:
            with open(self.config_path, 'r') as f:
                configs = json.load(f)
            
            for config_dict in configs.get("connectors", []):
                config = ConnectorConfig(
                    connector_id=config_dict["connector_id"],
                    connector_type=ConnectorType(config_dict["connector_type"]),
                    name=config_dict["name"],
                    description=config_dict.get("description", ""),
                    config=config_dict.get("config", {}),
                    credentials=config_dict.get("credentials", {}),
                    enabled=config_dict.get("enabled", True)
                )
                self.registry.create_instance(config)
                
        except Exception as e:
            logger.warning(f"Failed to load connector configs: {e}", title="ConnectorManager")
    
    def save_configs(self):
        """Save connector configurations to file"""
        if not self.config_path:
            return
        
        configs = []
        for connector_id, config in self.registry._configs.items():
            configs.append({
                "connector_id": config.connector_id,
                "connector_type": config.connector_type.value,
                "name": config.name,
                "description": config.description,
                "config": config.config,
                "enabled": config.enabled
                # Note: credentials are not saved for security
            })
        
        with open(self.config_path, 'w') as f:
            json.dump({"connectors": configs}, f, indent=2)


# Global connector manager instance
connector_manager = ConnectorManager()

