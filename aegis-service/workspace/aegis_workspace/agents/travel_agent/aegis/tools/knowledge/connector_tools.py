"""
Connector Tools for knowledge grounding
"""

import json
from typing import List, Optional, Dict, Any

from aegis.registry import register_tool
from aegis.knowledge.connector_manager import connector_manager


@register_tool("create_connector")
def create_connector(connector_type: str, name: str, config: dict,
                     credentials: dict = None, description: str = "",
                     context_variables: dict = None) -> str:
    """
    Create a new knowledge connector.
    
    Args:
        connector_type: Type of connector (database, api, file, cloud)
        name: Name identifier for the connector
        config: Connection configuration dictionary
        credentials: Authentication credentials (optional)
        description: Description of the connector
        
    Returns:
        JSON string with connector details
        
    Examples:
        - SQLite: connector_type="database", name="SQLite", config={"db_path": "data.db"}
        - REST API: connector_type="api", name="REST API", config={"base_url": "https://api.example.com"}
        - File: connector_type="file", name="FileSystem", config={"base_path": "./data"}
    """
    connector_id = connector_manager.create_connector(
        connector_type=connector_type,
        name=name,
        config=config,
        credentials=credentials,
        description=description
    )
    
    if connector_id:
        return json.dumps({
            "status": "success",
            "connector_id": connector_id,
            "type": connector_type,
            "name": name,
            "message": f"Connector created. Use query_connector('{connector_id}', ...) to query."
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create connector. Check connector type and configuration."
        }, indent=2)


@register_tool("list_connectors")
def list_connectors(connector_type: str = None, status: str = None,
                    context_variables: dict = None) -> str:
    """
    List all knowledge connectors.
    
    Args:
        connector_type: Filter by type (database, api, file, cloud)
        status: Filter by status (connected, disconnected, error)
        
    Returns:
        JSON string with list of connectors
    """
    connectors = connector_manager.list_connectors(
        connector_type=connector_type,
        status=status
    )
    
    stats = connector_manager.get_statistics()
    
    return json.dumps({
        "status": "success",
        "connectors": connectors,
        "statistics": {
            "total": stats["total_connectors"],
            "by_type": stats["by_type"],
            "by_status": stats["by_status"]
        }
    }, indent=2)


@register_tool("connect_connector")
def connect_connector(connector_id: str, context_variables: dict = None) -> str:
    """
    Establish connection for a connector.
    
    Args:
        connector_id: ID of the connector to connect
        
    Returns:
        JSON string with connection status
    """
    success = connector_manager.connect(connector_id)
    
    if success:
        return json.dumps({
            "status": "success",
            "connector_id": connector_id,
            "message": "Connected successfully"
        }, indent=2)
    else:
        status = connector_manager.get_connector_status(connector_id)
        error = status.get("last_error") if status else "Connector not found"
        return json.dumps({
            "status": "error",
            "connector_id": connector_id,
            "message": f"Connection failed: {error}"
        }, indent=2)


@register_tool("query_connector")
def query_connector(connector_id: str, query: str, params: dict = None,
                    use_cache: bool = True, context_variables: dict = None) -> str:
    """
    Execute a query on a knowledge connector.
    
    Args:
        connector_id: ID of the connector to query
        query: Query string (format depends on connector type)
        params: Query parameters
        use_cache: Whether to use cached results
        
    Returns:
        JSON string with query results
        
    Query formats by connector type:
        - Database: SQL query (e.g., "SELECT * FROM users WHERE id = 1")
        - REST API: "METHOD:endpoint" (e.g., "GET:/users", "POST:/users")
        - File: "action:path" (e.g., "read:config.json", "list:.", "search:keyword")
        - Cloud: "action:key" (e.g., "get:data.json", "list:prefix/")
    """
    result = connector_manager.query(
        connector_id=connector_id,
        query=query,
        params=params,
        use_cache=use_cache
    )
    
    if "error" in result:
        return json.dumps({
            "status": "error",
            "connector_id": connector_id,
            "error": result["error"]
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "connector_id": connector_id,
        "from_cache": result.get("from_cache", False),
        "result": result.get("result")
    }, indent=2)


@register_tool("search_knowledge")
def search_knowledge(search_term: str, connector_ids: List[str] = None,
                     context_variables: dict = None) -> str:
    """
    Search across multiple knowledge connectors.
    
    Args:
        search_term: Term to search for
        connector_ids: Optional list of specific connectors to search
        
    Returns:
        JSON string with search results from all connectors
    """
    results = connector_manager.search(search_term, connector_ids)
    
    return json.dumps({
        "status": "success",
        "search_term": search_term,
        "connectors_searched": results["total_connectors_searched"],
        "results": results["results"]
    }, indent=2)


@register_tool("query_all_connectors")
def query_all_connectors(query: str, params: dict = None,
                         connector_types: List[str] = None,
                         context_variables: dict = None) -> str:
    """
    Query all connected connectors with the same query.
    
    Args:
        query: Query string
        params: Query parameters
        connector_types: Filter by connector types
        
    Returns:
        JSON string with combined results from all connectors
    """
    results = connector_manager.query_all(query, params, connector_types)
    
    return json.dumps({
        "status": "success",
        "query": results["query"],
        "connector_count": results["connector_count"],
        "results": results["results"]
    }, indent=2)


@register_tool("test_connector")
def test_connector(connector_id: str, context_variables: dict = None) -> str:
    """
    Test a connector's connection.
    
    Args:
        connector_id: ID of the connector to test
        
    Returns:
        JSON string with test results
    """
    result = connector_manager.test_connector(connector_id)
    
    return json.dumps({
        "status": "success" if result["success"] else "error",
        "connector_id": connector_id,
        "connection_healthy": result["success"],
        "connector_status": result.get("status"),
        "error": result.get("error")
    }, indent=2)


@register_tool("remove_connector")
def remove_connector(connector_id: str, context_variables: dict = None) -> str:
    """
    Remove a knowledge connector.
    
    Args:
        connector_id: ID of the connector to remove
        
    Returns:
        JSON string with removal status
    """
    success = connector_manager.remove_connector(connector_id)
    
    if success:
        return json.dumps({
            "status": "success",
            "connector_id": connector_id,
            "message": "Connector removed successfully"
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Connector {connector_id} not found"
        }, indent=2)


@register_tool("get_connector_status")
def get_connector_status(connector_id: str, context_variables: dict = None) -> str:
    """
    Get detailed status of a connector.
    
    Args:
        connector_id: ID of the connector
        
    Returns:
        JSON string with connector status details
    """
    status = connector_manager.get_connector_status(connector_id)
    
    if status:
        return json.dumps({
            "status": "success",
            "connector": status
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": f"Connector {connector_id} not found"
        }, indent=2)


@register_tool("get_connector_statistics")
def get_connector_statistics(context_variables: dict = None) -> str:
    """
    Get statistics about all connectors.
    
    Returns:
        JSON string with connector statistics
    """
    stats = connector_manager.get_statistics()
    
    return json.dumps({
        "status": "success",
        "statistics": stats
    }, indent=2)


@register_tool("clear_connector_cache")
def clear_connector_cache(context_variables: dict = None) -> str:
    """
    Clear the query cache for all connectors.
    
    Returns:
        JSON string with cache clear status
    """
    cache_size = len(connector_manager.query_cache)
    connector_manager.clear_cache()
    
    return json.dumps({
        "status": "success",
        "entries_cleared": cache_size,
        "message": "Query cache cleared"
    }, indent=2)

