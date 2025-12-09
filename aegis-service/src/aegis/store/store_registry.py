"""
Store Registry for managing agent templates and versions
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class TemplateCategory(str, Enum):
    """Categories for agent templates"""
    GENERAL = "general"
    DATA_ANALYSIS = "data_analysis"
    WEB = "web"
    FILE_MANAGEMENT = "file_management"
    CODE = "code"
    RESEARCH = "research"
    AUTOMATION = "automation"
    CUSTOMER_SERVICE = "customer_service"
    INTEGRATION = "integration"
    CUSTOM = "custom"


@dataclass
class AgentVersion:
    """Version information for an agent"""
    version: str
    release_date: str
    changelog: str = ""
    min_aegis_version: str = "1.0.0"
    deprecated: bool = False


@dataclass
class AgentMetadata:
    """Metadata for a store agent"""
    agent_id: str
    name: str
    description: str
    category: TemplateCategory
    author: str = "Aegis"
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    versions: List[AgentVersion] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    reviews: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    requirements: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    documentation: str = ""
    icon: str = ""


class StoreRegistry:
    """
    Registry for agent templates in the store.
    """
    
    _agents: Dict[str, AgentMetadata] = {}
    _templates: Dict[str, str] = {}  # agent_id -> template code
    _installed: Dict[str, str] = {}  # agent_id -> installed version
    
    @classmethod
    def register(cls, metadata: AgentMetadata, template_code: str):
        """
        Register an agent in the store.
        
        Args:
            metadata: Agent metadata
            template_code: Python code template for the agent
        """
        cls._agents[metadata.agent_id] = metadata
        cls._templates[metadata.agent_id] = template_code
    
    @classmethod
    def get(cls, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent metadata by ID"""
        return cls._agents.get(agent_id)
    
    @classmethod
    def get_template(cls, agent_id: str) -> Optional[str]:
        """Get agent template code"""
        return cls._templates.get(agent_id)
    
    @classmethod
    def list_agents(cls, category: TemplateCategory = None,
                    tags: List[str] = None) -> List[AgentMetadata]:
        """
        List all agents in the store.
        
        Args:
            category: Filter by category
            tags: Filter by tags
            
        Returns:
            List of agent metadata
        """
        agents = list(cls._agents.values())
        
        if category:
            agents = [a for a in agents if a.category == category]
        
        if tags:
            agents = [
                a for a in agents 
                if any(tag in a.tags for tag in tags)
            ]
        
        return agents
    
    @classmethod
    def search(cls, query: str) -> List[AgentMetadata]:
        """
        Search agents by name, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            Matching agents
        """
        query_lower = query.lower()
        results = []
        
        for agent in cls._agents.values():
            if (query_lower in agent.name.lower() or
                query_lower in agent.description.lower() or
                any(query_lower in tag.lower() for tag in agent.tags)):
                results.append(agent)
        
        return results
    
    @classmethod
    def mark_installed(cls, agent_id: str, version: str):
        """Mark an agent as installed"""
        cls._installed[agent_id] = version
        if agent_id in cls._agents:
            cls._agents[agent_id].downloads += 1
    
    @classmethod
    def is_installed(cls, agent_id: str) -> bool:
        """Check if an agent is installed"""
        return agent_id in cls._installed
    
    @classmethod
    def get_installed_version(cls, agent_id: str) -> Optional[str]:
        """Get installed version of an agent"""
        return cls._installed.get(agent_id)
    
    @classmethod
    def unmark_installed(cls, agent_id: str):
        """Unmark an agent as installed"""
        if agent_id in cls._installed:
            del cls._installed[agent_id]
    
    @classmethod
    def list_installed(cls) -> List[Dict[str, str]]:
        """List all installed agents"""
        return [
            {
                "agent_id": agent_id,
                "version": version,
                "name": cls._agents[agent_id].name if agent_id in cls._agents else "Unknown"
            }
            for agent_id, version in cls._installed.items()
        ]
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all available categories"""
        return [cat.value for cat in TemplateCategory]
    
    @classmethod
    def get_popular_tags(cls, limit: int = 20) -> List[tuple]:
        """Get most popular tags"""
        tag_counts: Dict[str, int] = {}
        
        for agent in cls._agents.values():
            for tag in agent.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags[:limit]
    
    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Get store statistics"""
        categories = {}
        for agent in cls._agents.values():
            cat = agent.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_agents": len(cls._agents),
            "installed_agents": len(cls._installed),
            "categories": categories,
            "total_downloads": sum(a.downloads for a in cls._agents.values())
        }

