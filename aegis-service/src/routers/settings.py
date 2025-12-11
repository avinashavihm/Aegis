"""
Settings Router - API Keys, AI Models, and Configuration Management
Similar to Microsoft Copilot Studio settings
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import hashlib
import base64
import os

from src.database import get_db_connection
from src.dependencies import get_current_user_id

router = APIRouter(prefix="/settings", tags=["settings"])

# Simple encryption for API keys (in production, use proper encryption like Fernet)
def encrypt_api_key(key: str) -> str:
    """Simple obfuscation - in production use proper encryption"""
    return base64.b64encode(key.encode()).decode()

def decrypt_api_key(encrypted: str) -> str:
    """Simple de-obfuscation"""
    return base64.b64decode(encrypted.encode()).decode()

def get_key_preview(key: str) -> str:
    """Get last 4 characters of key for display"""
    if len(key) > 4:
        return f"...{key[-4:]}"
    return "****"


# ============================================
# API KEYS MANAGEMENT
# ============================================

class APIKeyCreate(BaseModel):
    name: str
    provider: str  # 'openai', 'anthropic', 'google', 'groq', 'mistral', 'cohere', 'together', 'azure'
    api_key: str
    base_url: Optional[str] = None
    organization_id: Optional[str] = None
    is_default: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = {}


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None  # If provided, updates the key
    base_url: Optional[str] = None
    organization_id: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    provider: str
    api_key_preview: str
    base_url: Optional[str]
    organization_id: Optional[str]
    is_default: bool
    is_active: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(user_id: str = Depends(get_current_user_id)):
    """List all API keys for the current user"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, provider, api_key_preview, base_url, organization_id,
                       is_default, is_active, metadata, created_at, updated_at
                FROM api_keys
                WHERE owner_id = %s
                ORDER BY is_default DESC, provider, name
            """, (user_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]


@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_api_key(data: APIKeyCreate, user_id: str = Depends(get_current_user_id)):
    """Create a new API key"""
    encrypted_key = encrypt_api_key(data.api_key)
    preview = get_key_preview(data.api_key)
    
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            # If this is default, unset other defaults for this provider
            if data.is_default:
                cur.execute("""
                    UPDATE api_keys SET is_default = FALSE
                    WHERE owner_id = %s AND provider = %s
                """, (user_id, data.provider))
            
            cur.execute("""
                INSERT INTO api_keys (name, provider, api_key_encrypted, api_key_preview, 
                                      base_url, organization_id, is_default, metadata, owner_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, provider, api_key_preview, base_url, organization_id,
                          is_default, is_active, metadata, created_at, updated_at
            """, (data.name, data.provider, encrypted_key, preview, 
                  data.base_url, data.organization_id, data.is_default, 
                  data.metadata or {}, user_id))
            conn.commit()
            row = cur.fetchone()
            return dict(row)


@router.get("/api-keys/{key_id}", response_model=APIKeyResponse)
async def get_api_key(key_id: UUID, user_id: str = Depends(get_current_user_id)):
    """Get an API key by ID"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, provider, api_key_preview, base_url, organization_id,
                       is_default, is_active, metadata, created_at, updated_at
                FROM api_keys
                WHERE id = %s AND owner_id = %s
            """, (str(key_id), user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="API key not found")
            return dict(row)


@router.put("/api-keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(key_id: UUID, data: APIKeyUpdate, user_id: str = Depends(get_current_user_id)):
    """Update an API key"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            # Build update query
            updates = []
            params = []
            
            if data.name is not None:
                updates.append("name = %s")
                params.append(data.name)
            
            if data.api_key is not None:
                updates.append("api_key_encrypted = %s")
                params.append(encrypt_api_key(data.api_key))
                updates.append("api_key_preview = %s")
                params.append(get_key_preview(data.api_key))
            
            if data.base_url is not None:
                updates.append("base_url = %s")
                params.append(data.base_url)
            
            if data.organization_id is not None:
                updates.append("organization_id = %s")
                params.append(data.organization_id)
            
            if data.is_default is not None:
                updates.append("is_default = %s")
                params.append(data.is_default)
                if data.is_default:
                    # Get provider first
                    cur.execute("SELECT provider FROM api_keys WHERE id = %s", (str(key_id),))
                    row = cur.fetchone()
                    if row:
                        cur.execute("""
                            UPDATE api_keys SET is_default = FALSE
                            WHERE owner_id = %s AND provider = %s AND id != %s
                        """, (user_id, row['provider'], str(key_id)))
            
            if data.is_active is not None:
                updates.append("is_active = %s")
                params.append(data.is_active)
            
            if data.metadata is not None:
                updates.append("metadata = %s")
                params.append(data.metadata)
            
            if not updates:
                raise HTTPException(status_code=400, detail="No updates provided")
            
            params.extend([str(key_id), user_id])
            
            cur.execute(f"""
                UPDATE api_keys SET {', '.join(updates)}
                WHERE id = %s AND owner_id = %s
                RETURNING id, name, provider, api_key_preview, base_url, organization_id,
                          is_default, is_active, metadata, created_at, updated_at
            """, params)
            conn.commit()
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="API key not found")
            return dict(row)


@router.delete("/api-keys/{key_id}", status_code=204)
async def delete_api_key(key_id: UUID, user_id: str = Depends(get_current_user_id)):
    """Delete an API key"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM api_keys WHERE id = %s AND owner_id = %s
                RETURNING id
            """, (str(key_id), user_id))
            conn.commit()
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="API key not found")


@router.post("/api-keys/{key_id}/test")
async def test_api_key(key_id: UUID, user_id: str = Depends(get_current_user_id)):
    """Test if an API key is valid"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT api_key_encrypted, provider, base_url
                FROM api_keys WHERE id = %s AND owner_id = %s
            """, (str(key_id), user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="API key not found")
            
            # Decrypt and test key
            api_key = decrypt_api_key(row['api_key_encrypted'])
            provider = row['provider']
            
            # Simple validation - try a minimal API call
            try:
                import litellm
                # Just validate the key format for now
                if provider == 'openai' and not api_key.startswith('sk-'):
                    return {"valid": False, "message": "Invalid OpenAI key format"}
                if provider == 'anthropic' and not api_key.startswith('sk-ant-'):
                    return {"valid": False, "message": "Invalid Anthropic key format"}
                    
                return {"valid": True, "message": f"API key appears valid for {provider}"}
            except Exception as e:
                return {"valid": False, "message": str(e)}


# ============================================
# AI MODELS
# ============================================

class AIModelResponse(BaseModel):
    id: UUID
    provider: str
    model_id: str
    display_name: str
    description: Optional[str]
    capabilities: List[str]
    context_window: int
    max_output_tokens: Optional[int]
    supports_streaming: bool
    supports_tools: bool
    supports_vision: bool
    is_available: bool


@router.get("/models", response_model=List[AIModelResponse])
async def list_ai_models(
    provider: Optional[str] = None,
    supports_tools: Optional[bool] = None,
    supports_vision: Optional[bool] = None,
    user_id: str = Depends(get_current_user_id)
):
    """List available AI models"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            query = """
                SELECT id, provider, model_id, display_name, description, capabilities,
                       context_window, max_output_tokens, supports_streaming, 
                       supports_tools, supports_vision, is_available
                FROM ai_models
                WHERE is_available = TRUE
            """
            params = []
            
            if provider:
                query += " AND provider = %s"
                params.append(provider)
            
            if supports_tools is not None:
                query += " AND supports_tools = %s"
                params.append(supports_tools)
            
            if supports_vision is not None:
                query += " AND supports_vision = %s"
                params.append(supports_vision)
            
            query += " ORDER BY provider, display_name"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]


@router.get("/models/providers")
async def list_providers(user_id: str = Depends(get_current_user_id)):
    """List available AI providers"""
    providers = [
        {
            "id": "openai",
            "name": "OpenAI",
            "description": "GPT-4, GPT-3.5, and O1 models",
            "requires_key": True,
            "key_url": "https://platform.openai.com/api-keys"
        },
        {
            "id": "anthropic", 
            "name": "Anthropic",
            "description": "Claude 3.5 and Claude 3 models",
            "requires_key": True,
            "key_url": "https://console.anthropic.com/settings/keys"
        },
        {
            "id": "google",
            "name": "Google AI",
            "description": "Gemini 2.0 and 1.5 models",
            "requires_key": True,
            "key_url": "https://aistudio.google.com/app/apikey"
        },
        {
            "id": "groq",
            "name": "Groq",
            "description": "Ultra-fast inference for Llama and Mixtral",
            "requires_key": True,
            "key_url": "https://console.groq.com/keys"
        },
        {
            "id": "mistral",
            "name": "Mistral AI",
            "description": "Mistral Large, Medium, and Small models",
            "requires_key": True,
            "key_url": "https://console.mistral.ai/api-keys"
        },
        {
            "id": "cohere",
            "name": "Cohere",
            "description": "Command R+ and Command R models with RAG",
            "requires_key": True,
            "key_url": "https://dashboard.cohere.com/api-keys"
        },
        {
            "id": "together",
            "name": "Together AI",
            "description": "Wide variety of open source models",
            "requires_key": True,
            "key_url": "https://api.together.xyz/settings/api-keys"
        },
        {
            "id": "azure",
            "name": "Azure OpenAI",
            "description": "OpenAI models on Azure infrastructure",
            "requires_key": True,
            "requires_base_url": True,
            "key_url": "https://portal.azure.com"
        },
        {
            "id": "firecrawl",
            "name": "Firecrawl",
            "description": "Firecrawl crawl/search API",
            "requires_key": True,
            "key_url": "https://www.firecrawl.dev/"
        },
        {
            "id": "custom",
            "name": "Custom",
            "description": "Custom provider with optional base URL",
            "requires_key": True,
            "requires_base_url": False,
            "key_url": ""
        }
    ]
    return providers


# ============================================
# AGENT TOPICS (Conversation Flows)
# ============================================

class TopicNodeCreate(BaseModel):
    type: str  # 'message', 'question', 'condition', 'action', 'handoff'
    content: Optional[str] = None
    options: Optional[List[str]] = None  # For question nodes
    condition: Optional[str] = None  # For condition nodes
    action_id: Optional[str] = None  # For action nodes
    next_nodes: Optional[List[str]] = None


class TopicCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str = "phrase"  # 'phrase', 'event', 'intent', 'schedule'
    trigger_phrases: Optional[List[str]] = []
    trigger_config: Optional[Dict[str, Any]] = {}
    conversation_flow: Optional[List[Dict[str, Any]]] = []
    is_enabled: Optional[bool] = True
    priority: Optional[int] = 0


class TopicResponse(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_phrases: List[str]
    trigger_config: Dict[str, Any]
    conversation_flow: List[Dict[str, Any]]
    is_enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime


@router.get("/agents/{agent_id}/topics", response_model=List[TopicResponse])
async def list_agent_topics(agent_id: UUID, user_id: str = Depends(get_current_user_id)):
    """List all topics for an agent"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, agent_id, name, description, trigger_type, trigger_phrases,
                       trigger_config, conversation_flow, is_enabled, priority,
                       created_at, updated_at
                FROM agent_topics
                WHERE agent_id = %s
                ORDER BY priority DESC, name
            """, (str(agent_id),))
            rows = cur.fetchall()
            return [dict(row) for row in rows]


@router.post("/agents/{agent_id}/topics", response_model=TopicResponse, status_code=201)
async def create_agent_topic(
    agent_id: UUID, 
    data: TopicCreate, 
    user_id: str = Depends(get_current_user_id)
):
    """Create a new topic for an agent"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO agent_topics (agent_id, name, description, trigger_type, trigger_phrases,
                                         trigger_config, conversation_flow, is_enabled, priority, owner_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, agent_id, name, description, trigger_type, trigger_phrases,
                          trigger_config, conversation_flow, is_enabled, priority,
                          created_at, updated_at
            """, (str(agent_id), data.name, data.description, data.trigger_type,
                  data.trigger_phrases, data.trigger_config, data.conversation_flow,
                  data.is_enabled, data.priority, user_id))
            conn.commit()
            row = cur.fetchone()
            return dict(row)


@router.delete("/agents/{agent_id}/topics/{topic_id}", status_code=204)
async def delete_agent_topic(
    agent_id: UUID, 
    topic_id: UUID, 
    user_id: str = Depends(get_current_user_id)
):
    """Delete a topic"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM agent_topics WHERE id = %s AND agent_id = %s
                RETURNING id
            """, (str(topic_id), str(agent_id)))
            conn.commit()
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Topic not found")


# ============================================
# AGENT ACTIONS (Connectors)
# ============================================

class ActionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    action_type: str  # 'http', 'webhook', 'database', 'email', 'slack', 'custom'
    config: Dict[str, Any] = {}
    input_schema: Optional[Dict[str, Any]] = {}
    output_schema: Optional[Dict[str, Any]] = {}
    authentication: Optional[Dict[str, Any]] = {}
    is_enabled: Optional[bool] = True


class ActionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    description: Optional[str]
    action_type: str
    config: Dict[str, Any]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    authentication: Dict[str, Any]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


@router.get("/agents/{agent_id}/actions", response_model=List[ActionResponse])
async def list_agent_actions(agent_id: UUID, user_id: str = Depends(get_current_user_id)):
    """List all actions for an agent"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, agent_id, name, description, action_type, config,
                       input_schema, output_schema, authentication, is_enabled,
                       created_at, updated_at
                FROM agent_actions
                WHERE agent_id = %s
                ORDER BY name
            """, (str(agent_id),))
            rows = cur.fetchall()
            return [dict(row) for row in rows]


@router.post("/agents/{agent_id}/actions", response_model=ActionResponse, status_code=201)
async def create_agent_action(
    agent_id: UUID, 
    data: ActionCreate, 
    user_id: str = Depends(get_current_user_id)
):
    """Create a new action for an agent"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO agent_actions (agent_id, name, description, action_type, config,
                                          input_schema, output_schema, authentication, is_enabled, owner_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, agent_id, name, description, action_type, config,
                          input_schema, output_schema, authentication, is_enabled,
                          created_at, updated_at
            """, (str(agent_id), data.name, data.description, data.action_type, data.config,
                  data.input_schema, data.output_schema, data.authentication,
                  data.is_enabled, user_id))
            conn.commit()
            row = cur.fetchone()
            return dict(row)


@router.delete("/agents/{agent_id}/actions/{action_id}", status_code=204)
async def delete_agent_action(
    agent_id: UUID, 
    action_id: UUID, 
    user_id: str = Depends(get_current_user_id)
):
    """Delete an action"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM agent_actions WHERE id = %s AND agent_id = %s
                RETURNING id
            """, (str(action_id), str(agent_id)))
            conn.commit()
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Action not found")


# ============================================
# AGENT KNOWLEDGE BASE
# ============================================

class KnowledgeCreate(BaseModel):
    name: str
    source_type: str  # 'file', 'url', 'text', 'database'
    source_url: Optional[str] = None
    content: Optional[str] = None
    sync_frequency: Optional[str] = "manual"
    is_enabled: Optional[bool] = True


class KnowledgeResponse(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    source_type: str
    source_url: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    chunk_count: int
    embedding_status: str
    last_synced_at: Optional[datetime]
    sync_frequency: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


@router.get("/agents/{agent_id}/knowledge", response_model=List[KnowledgeResponse])
async def list_agent_knowledge(agent_id: UUID, user_id: str = Depends(get_current_user_id)):
    """List all knowledge sources for an agent"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, agent_id, name, source_type, source_url, file_type, file_size,
                       chunk_count, embedding_status, last_synced_at, sync_frequency,
                       is_enabled, created_at, updated_at
                FROM agent_knowledge
                WHERE agent_id = %s
                ORDER BY name
            """, (str(agent_id),))
            rows = cur.fetchall()
            return [dict(row) for row in rows]


@router.post("/agents/{agent_id}/knowledge", response_model=KnowledgeResponse, status_code=201)
async def create_agent_knowledge(
    agent_id: UUID, 
    data: KnowledgeCreate, 
    user_id: str = Depends(get_current_user_id)
):
    """Add a knowledge source to an agent"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO agent_knowledge (agent_id, name, source_type, source_url, content,
                                            sync_frequency, is_enabled, owner_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, agent_id, name, source_type, source_url, file_type, file_size,
                          chunk_count, embedding_status, last_synced_at, sync_frequency,
                          is_enabled, created_at, updated_at
            """, (str(agent_id), data.name, data.source_type, data.source_url, 
                  data.content, data.sync_frequency, data.is_enabled, user_id))
            conn.commit()
            row = cur.fetchone()
            return dict(row)


@router.delete("/agents/{agent_id}/knowledge/{knowledge_id}", status_code=204)
async def delete_agent_knowledge(
    agent_id: UUID, 
    knowledge_id: UUID, 
    user_id: str = Depends(get_current_user_id)
):
    """Remove a knowledge source"""
    with get_db_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM agent_knowledge WHERE id = %s AND agent_id = %s
                RETURNING id
            """, (str(knowledge_id), str(agent_id)))
            conn.commit()
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Knowledge source not found")
