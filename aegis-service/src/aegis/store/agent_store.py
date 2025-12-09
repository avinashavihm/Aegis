"""
Agent Store for discovering, installing, and managing agent templates
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from aegis.store.store_registry import StoreRegistry, AgentMetadata, TemplateCategory
from aegis.logger import LoggerManager

logger = LoggerManager.get_logger()


class AgentStore:
    """
    Agent Store for discovering and installing pre-built agents.
    """
    
    def __init__(self, workspace_path: str = None):
        """
        Initialize the agent store.
        
        Args:
            workspace_path: Path to install agents
        """
        self.workspace_path = workspace_path or os.path.join(os.getcwd(), "workspace", "aegis_workspace", "agents")
        self.registry = StoreRegistry
        
        # Ensure workspace exists
        os.makedirs(self.workspace_path, exist_ok=True)
    
    def browse(self, category: str = None, tags: List[str] = None,
               sort_by: str = "downloads") -> List[Dict[str, Any]]:
        """
        Browse available agents in the store.
        
        Args:
            category: Filter by category
            tags: Filter by tags
            sort_by: Sort by field (downloads, rating, name, updated)
            
        Returns:
            List of agent summaries
        """
        cat = TemplateCategory(category) if category else None
        agents = self.registry.list_agents(category=cat, tags=tags)
        
        # Sort
        if sort_by == "downloads":
            agents.sort(key=lambda a: a.downloads, reverse=True)
        elif sort_by == "rating":
            agents.sort(key=lambda a: a.rating, reverse=True)
        elif sort_by == "name":
            agents.sort(key=lambda a: a.name)
        elif sort_by == "updated":
            agents.sort(key=lambda a: a.updated_at, reverse=True)
        
        # Convert to summaries
        summaries = []
        for agent in agents:
            summaries.append({
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description[:100] + "..." if len(agent.description) > 100 else agent.description,
                "category": agent.category.value,
                "version": agent.version,
                "downloads": agent.downloads,
                "rating": agent.rating,
                "tags": agent.tags[:5],
                "installed": self.registry.is_installed(agent.agent_id)
            })
        
        return summaries
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for agents.
        
        Args:
            query: Search query
            
        Returns:
            List of matching agent summaries
        """
        agents = self.registry.search(query)
        
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description[:100] + "..." if len(a.description) > 100 else a.description,
                "category": a.category.value,
                "tags": a.tags[:5],
                "installed": self.registry.is_installed(a.agent_id)
            }
            for a in agents
        ]
    
    def get_details(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Full agent details
        """
        agent = self.registry.get(agent_id)
        if not agent:
            return None
        
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "category": agent.category.value,
            "author": agent.author,
            "version": agent.version,
            "tags": agent.tags,
            "downloads": agent.downloads,
            "rating": agent.rating,
            "reviews": agent.reviews,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "requirements": agent.requirements,
            "tools_used": agent.tools_used,
            "examples": agent.examples,
            "documentation": agent.documentation,
            "installed": self.registry.is_installed(agent_id),
            "installed_version": self.registry.get_installed_version(agent_id)
        }
    
    def install(self, agent_id: str, customize: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Install an agent from the store.
        
        Args:
            agent_id: Agent ID to install
            customize: Optional customization parameters
            
        Returns:
            Installation result
        """
        agent = self.registry.get(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found in store"}
        
        template = self.registry.get_template(agent_id)
        if not template:
            return {"success": False, "error": f"Template not found for {agent_id}"}
        
        # Apply customizations if provided
        if customize:
            template = self._apply_customizations(template, customize)
        
        # Generate file name
        file_name = f"{agent_id.replace('-', '_')}.py"
        file_path = os.path.join(self.workspace_path, file_name)
        
        try:
            # Write the agent file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(template)
            
            # Mark as installed
            self.registry.mark_installed(agent_id, agent.version)
            
            logger.info(f"Installed agent: {agent.name} ({agent_id})", title="AgentStore")
            
            return {
                "success": True,
                "agent_id": agent_id,
                "name": agent.name,
                "version": agent.version,
                "file_path": file_path,
                "message": f"Agent '{agent.name}' installed successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _apply_customizations(self, template: str, customize: Dict[str, Any]) -> str:
        """Apply customizations to a template"""
        # Replace placeholder variables
        for key, value in customize.items():
            placeholder = f"{{{{${key}}}}}"
            template = template.replace(placeholder, str(value))
        
        return template
    
    def uninstall(self, agent_id: str) -> Dict[str, Any]:
        """
        Uninstall an agent.
        
        Args:
            agent_id: Agent ID to uninstall
            
        Returns:
            Uninstall result
        """
        if not self.registry.is_installed(agent_id):
            return {"success": False, "error": f"Agent {agent_id} is not installed"}
        
        file_name = f"{agent_id.replace('-', '_')}.py"
        file_path = os.path.join(self.workspace_path, file_name)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            
            self.registry.unmark_installed(agent_id)
            
            logger.info(f"Uninstalled agent: {agent_id}", title="AgentStore")
            
            return {
                "success": True,
                "agent_id": agent_id,
                "message": f"Agent '{agent_id}' uninstalled successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update(self, agent_id: str) -> Dict[str, Any]:
        """
        Update an installed agent to the latest version.
        
        Args:
            agent_id: Agent ID to update
            
        Returns:
            Update result
        """
        installed_version = self.registry.get_installed_version(agent_id)
        if not installed_version:
            return {"success": False, "error": f"Agent {agent_id} is not installed"}
        
        agent = self.registry.get(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent {agent_id} not found in store"}
        
        if installed_version == agent.version:
            return {
                "success": True,
                "agent_id": agent_id,
                "message": f"Agent is already at the latest version ({agent.version})"
            }
        
        # Uninstall and reinstall
        self.uninstall(agent_id)
        return self.install(agent_id)
    
    def list_installed(self) -> List[Dict[str, Any]]:
        """
        List all installed agents.
        
        Returns:
            List of installed agent summaries
        """
        installed = self.registry.list_installed()
        
        result = []
        for item in installed:
            agent = self.registry.get(item["agent_id"])
            if agent:
                result.append({
                    "agent_id": item["agent_id"],
                    "name": agent.name,
                    "installed_version": item["version"],
                    "latest_version": agent.version,
                    "update_available": item["version"] != agent.version,
                    "category": agent.category.value
                })
        
        return result
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get all available categories with counts.
        
        Returns:
            List of categories with agent counts
        """
        stats = self.registry.get_statistics()
        categories = []
        
        for cat in TemplateCategory:
            count = stats["categories"].get(cat.value, 0)
            categories.append({
                "id": cat.value,
                "name": cat.value.replace("_", " ").title(),
                "count": count
            })
        
        return categories
    
    def get_popular_tags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get popular tags.
        
        Args:
            limit: Maximum number of tags
            
        Returns:
            List of tags with counts
        """
        tags = self.registry.get_popular_tags(limit)
        return [{"tag": tag, "count": count} for tag, count in tags]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics"""
        return self.registry.get_statistics()
    
    def export_agent(self, agent_id: str, export_path: str = None) -> Dict[str, Any]:
        """
        Export an installed agent.
        
        Args:
            agent_id: Agent ID to export
            export_path: Path to export to
            
        Returns:
            Export result
        """
        agent = self.registry.get(agent_id)
        template = self.registry.get_template(agent_id)
        
        if not agent or not template:
            return {"success": False, "error": f"Agent {agent_id} not found"}
        
        export_data = {
            "metadata": {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "category": agent.category.value,
                "author": agent.author,
                "version": agent.version,
                "tags": agent.tags,
                "tools_used": agent.tools_used,
                "requirements": agent.requirements,
                "examples": agent.examples
            },
            "template_code": template,
            "exported_at": datetime.now().isoformat()
        }
        
        if export_path:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            return {"success": True, "export_path": export_path}
        
        return {"success": True, "data": export_data}
    
    def import_agent(self, import_path: str = None, import_data: Dict = None) -> Dict[str, Any]:
        """
        Import an agent from export file or data.
        
        Args:
            import_path: Path to import file
            import_data: Direct import data
            
        Returns:
            Import result
        """
        if import_path:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif import_data:
            data = import_data
        else:
            return {"success": False, "error": "No import source provided"}
        
        try:
            metadata = AgentMetadata(
                agent_id=data["metadata"]["agent_id"],
                name=data["metadata"]["name"],
                description=data["metadata"]["description"],
                category=TemplateCategory(data["metadata"].get("category", "custom")),
                author=data["metadata"].get("author", "Imported"),
                version=data["metadata"].get("version", "1.0.0"),
                tags=data["metadata"].get("tags", []),
                tools_used=data["metadata"].get("tools_used", []),
                requirements=data["metadata"].get("requirements", []),
                examples=data["metadata"].get("examples", [])
            )
            
            self.registry.register(metadata, data["template_code"])
            
            return {
                "success": True,
                "agent_id": metadata.agent_id,
                "name": metadata.name,
                "message": f"Agent '{metadata.name}' imported successfully"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global agent store instance
agent_store = AgentStore()

