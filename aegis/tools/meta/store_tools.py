"""
Store Tools for browsing and installing agents from the Agent Store
"""

import json
from typing import List, Optional

from aegis.registry import register_tool
from aegis.store.agent_store import agent_store


@register_tool("browse_store")
def browse_store(category: str = None, tags: str = None,
                 sort_by: str = "downloads", context_variables: dict = None) -> str:
    """
    Browse available agents in the Agent Store.
    
    Args:
        category: Filter by category (data_analysis, web, code, research, etc.)
        tags: Comma-separated tags to filter by
        sort_by: Sort results by (downloads, rating, name, updated)
        
    Returns:
        JSON string with available agents
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    
    agents = agent_store.browse(
        category=category,
        tags=tag_list,
        sort_by=sort_by
    )
    
    return json.dumps({
        "status": "success",
        "total_agents": len(agents),
        "agents": agents,
        "message": f"Found {len(agents)} agents" + (f" in category '{category}'" if category else "")
    }, indent=2)


@register_tool("search_store")
def search_store(query: str, context_variables: dict = None) -> str:
    """
    Search for agents in the Agent Store.
    
    Args:
        query: Search query (searches name, description, and tags)
        
    Returns:
        JSON string with matching agents
    """
    agents = agent_store.search(query)
    
    return json.dumps({
        "status": "success",
        "query": query,
        "total_results": len(agents),
        "agents": agents
    }, indent=2)


@register_tool("get_agent_details")
def get_agent_details(agent_id: str, context_variables: dict = None) -> str:
    """
    Get detailed information about an agent in the store.
    
    Args:
        agent_id: The agent ID to get details for
        
    Returns:
        JSON string with full agent details
    """
    details = agent_store.get_details(agent_id)
    
    if not details:
        return json.dumps({
            "status": "error",
            "message": f"Agent '{agent_id}' not found in store"
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "agent": details
    }, indent=2)


@register_tool("install_from_store")
def install_from_store(agent_id: str, context_variables: dict = None) -> str:
    """
    Install an agent from the Agent Store.
    
    Args:
        agent_id: The agent ID to install
        
    Returns:
        JSON string with installation result
    """
    result = agent_store.install(agent_id)
    
    if result["success"]:
        return json.dumps({
            "status": "success",
            "agent_id": result["agent_id"],
            "name": result["name"],
            "version": result["version"],
            "file_path": result["file_path"],
            "message": result["message"],
            "next_steps": [
                f"Use run_agent(agent_name='{result['name']}', query='...') to run the agent",
                "The agent is now available in your workspace"
            ]
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Installation failed")
        }, indent=2)


@register_tool("uninstall_from_store")
def uninstall_from_store(agent_id: str, context_variables: dict = None) -> str:
    """
    Uninstall an agent that was installed from the store.
    
    Args:
        agent_id: The agent ID to uninstall
        
    Returns:
        JSON string with uninstall result
    """
    result = agent_store.uninstall(agent_id)
    
    if result["success"]:
        return json.dumps({
            "status": "success",
            "agent_id": result["agent_id"],
            "message": result["message"]
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Uninstall failed")
        }, indent=2)


@register_tool("update_store_agent")
def update_store_agent(agent_id: str, context_variables: dict = None) -> str:
    """
    Update an installed agent to the latest version.
    
    Args:
        agent_id: The agent ID to update
        
    Returns:
        JSON string with update result
    """
    result = agent_store.update(agent_id)
    
    return json.dumps({
        "status": "success" if result["success"] else "error",
        "agent_id": agent_id,
        "message": result.get("message", result.get("error", "Unknown result"))
    }, indent=2)


@register_tool("list_installed_store_agents")
def list_installed_store_agents(context_variables: dict = None) -> str:
    """
    List all agents installed from the store.
    
    Returns:
        JSON string with list of installed agents
    """
    installed = agent_store.list_installed()
    
    updates_available = sum(1 for a in installed if a.get("update_available", False))
    
    return json.dumps({
        "status": "success",
        "total_installed": len(installed),
        "updates_available": updates_available,
        "agents": installed
    }, indent=2)


@register_tool("get_store_categories")
def get_store_categories(context_variables: dict = None) -> str:
    """
    Get all available categories in the Agent Store.
    
    Returns:
        JSON string with categories and counts
    """
    categories = agent_store.get_categories()
    
    return json.dumps({
        "status": "success",
        "categories": categories
    }, indent=2)


@register_tool("get_store_statistics")
def get_store_statistics(context_variables: dict = None) -> str:
    """
    Get statistics about the Agent Store.
    
    Returns:
        JSON string with store statistics
    """
    stats = agent_store.get_statistics()
    popular_tags = agent_store.get_popular_tags(10)
    
    return json.dumps({
        "status": "success",
        "statistics": stats,
        "popular_tags": popular_tags
    }, indent=2)


@register_tool("export_agent")
def export_agent(agent_id: str, export_path: str = None,
                 context_variables: dict = None) -> str:
    """
    Export an agent to a file for sharing.
    
    Args:
        agent_id: The agent ID to export
        export_path: Path to save the export file
        
    Returns:
        JSON string with export result
    """
    result = agent_store.export_agent(agent_id, export_path)
    
    if result["success"]:
        if export_path:
            return json.dumps({
                "status": "success",
                "export_path": result["export_path"],
                "message": f"Agent exported to {export_path}"
            }, indent=2)
        else:
            return json.dumps({
                "status": "success",
                "data": result["data"],
                "message": "Agent exported successfully"
            }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Export failed")
        }, indent=2)


@register_tool("import_agent")
def import_agent(import_path: str, context_variables: dict = None) -> str:
    """
    Import an agent from an export file.
    
    Args:
        import_path: Path to the import file
        
    Returns:
        JSON string with import result
    """
    result = agent_store.import_agent(import_path=import_path)
    
    if result["success"]:
        return json.dumps({
            "status": "success",
            "agent_id": result["agent_id"],
            "name": result["name"],
            "message": result["message"],
            "next_steps": [
                f"Use install_from_store('{result['agent_id']}') to install the agent",
                f"Or browse_store() to see it in the store"
            ]
        }, indent=2)
    else:
        return json.dumps({
            "status": "error",
            "message": result.get("error", "Import failed")
        }, indent=2)

