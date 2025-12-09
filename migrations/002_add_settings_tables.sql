-- Migration: Add Settings Tables (API Keys, AI Models, Topics, Actions, Knowledge)
-- Run this after init.sql to add the new Copilot Studio-like features

-- ============================================
-- AI PROVIDER & API KEYS MANAGEMENT
-- ============================================

-- API Keys Table - stores user's API keys for different AI providers
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_key_preview VARCHAR(20),
    base_url TEXT,
    organization_id VARCHAR(100),
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI Models Table - stores available AI models configuration
CREATE TABLE IF NOT EXISTS ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    capabilities JSONB DEFAULT '[]',
    context_window INTEGER DEFAULT 4096,
    max_output_tokens INTEGER,
    input_cost_per_1k DECIMAL(10, 6),
    output_cost_per_1k DECIMAL(10, 6),
    supports_streaming BOOLEAN DEFAULT TRUE,
    supports_tools BOOLEAN DEFAULT TRUE,
    supports_vision BOOLEAN DEFAULT FALSE,
    is_available BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Topics Table - conversation flow topics
CREATE TABLE IF NOT EXISTS agent_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(50) NOT NULL DEFAULT 'phrase',
    trigger_phrases JSONB DEFAULT '[]',
    trigger_config JSONB DEFAULT '{}',
    conversation_flow JSONB DEFAULT '[]',
    is_enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Actions Table - external actions/connectors
CREATE TABLE IF NOT EXISTS agent_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    action_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    input_schema JSONB DEFAULT '{}',
    output_schema JSONB DEFAULT '{}',
    authentication JSONB DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent Knowledge Base Table - enhanced knowledge management
CREATE TABLE IF NOT EXISTS agent_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_url TEXT,
    content TEXT,
    content_hash VARCHAR(64),
    file_path TEXT,
    file_type VARCHAR(50),
    file_size BIGINT,
    chunk_count INTEGER DEFAULT 0,
    embedding_status VARCHAR(20) DEFAULT 'pending',
    last_synced_at TIMESTAMP WITH TIME ZONE,
    sync_frequency VARCHAR(20) DEFAULT 'manual',
    is_enabled BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_owner_id ON api_keys(owner_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_provider ON api_keys(provider);
CREATE INDEX IF NOT EXISTS idx_ai_models_provider ON ai_models(provider);
CREATE INDEX IF NOT EXISTS idx_ai_models_model_id ON ai_models(model_id);
CREATE INDEX IF NOT EXISTS idx_agent_topics_agent_id ON agent_topics(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_actions_agent_id ON agent_actions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent_id ON agent_knowledge(agent_id);

-- Triggers
DROP TRIGGER IF EXISTS update_api_keys_updated_at ON api_keys;
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_topics_updated_at ON agent_topics;
CREATE TRIGGER update_agent_topics_updated_at BEFORE UPDATE ON agent_topics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_actions_updated_at ON agent_actions;
CREATE TRIGGER update_agent_actions_updated_at BEFORE UPDATE ON agent_actions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_knowledge_updated_at ON agent_knowledge;
CREATE TRIGGER update_agent_knowledge_updated_at BEFORE UPDATE ON agent_knowledge FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_knowledge ENABLE ROW LEVEL SECURITY;

-- Force RLS
ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE ai_models FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_topics FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_actions FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_knowledge FORCE ROW LEVEL SECURITY;

-- RLS Policies for API Keys (private to owner)
DROP POLICY IF EXISTS api_keys_read_access ON api_keys;
CREATE POLICY api_keys_read_access ON api_keys FOR SELECT USING (
    current_user_is_admin() OR owner_id = current_setting('app.current_user_id', true)::uuid
);

DROP POLICY IF EXISTS api_keys_insert ON api_keys;
CREATE POLICY api_keys_insert ON api_keys FOR INSERT WITH CHECK (
    owner_id = current_setting('app.current_user_id', true)::uuid
);

DROP POLICY IF EXISTS api_keys_update ON api_keys;
CREATE POLICY api_keys_update ON api_keys FOR UPDATE USING (
    owner_id = current_setting('app.current_user_id', true)::uuid
);

DROP POLICY IF EXISTS api_keys_delete ON api_keys;
CREATE POLICY api_keys_delete ON api_keys FOR DELETE USING (
    owner_id = current_setting('app.current_user_id', true)::uuid
);

-- RLS Policies for AI Models (public read)
DROP POLICY IF EXISTS ai_models_read_access ON ai_models;
CREATE POLICY ai_models_read_access ON ai_models FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS ai_models_admin ON ai_models;
CREATE POLICY ai_models_admin ON ai_models FOR ALL USING (current_user_is_admin());

-- RLS Policies for Agent Topics
DROP POLICY IF EXISTS agent_topics_access ON agent_topics;
CREATE POLICY agent_topics_access ON agent_topics FOR ALL USING (
    current_user_is_admin()
    OR owner_id = current_setting('app.current_user_id', true)::uuid
    OR EXISTS (SELECT 1 FROM agents a WHERE a.id = agent_topics.agent_id AND a.owner_id = current_setting('app.current_user_id', true)::uuid)
);

-- RLS Policies for Agent Actions
DROP POLICY IF EXISTS agent_actions_access ON agent_actions;
CREATE POLICY agent_actions_access ON agent_actions FOR ALL USING (
    current_user_is_admin()
    OR owner_id = current_setting('app.current_user_id', true)::uuid
    OR EXISTS (SELECT 1 FROM agents a WHERE a.id = agent_actions.agent_id AND a.owner_id = current_setting('app.current_user_id', true)::uuid)
);

-- RLS Policies for Agent Knowledge
DROP POLICY IF EXISTS agent_knowledge_access ON agent_knowledge;
CREATE POLICY agent_knowledge_access ON agent_knowledge FOR ALL USING (
    current_user_is_admin()
    OR owner_id = current_setting('app.current_user_id', true)::uuid
    OR EXISTS (SELECT 1 FROM agents a WHERE a.id = agent_knowledge.agent_id AND a.owner_id = current_setting('app.current_user_id', true)::uuid)
);

-- Grant access to aegis_app
GRANT SELECT, INSERT, UPDATE, DELETE ON api_keys TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_models TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_topics TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_actions TO aegis_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_knowledge TO aegis_app;

-- Seed popular AI models
INSERT INTO ai_models (provider, model_id, display_name, description, capabilities, context_window, max_output_tokens, supports_streaming, supports_tools, supports_vision) VALUES
-- OpenAI Models
('openai', 'gpt-4o', 'GPT-4o', 'Most capable GPT-4 model with vision', '["chat", "vision", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, TRUE),
('openai', 'gpt-4o-mini', 'GPT-4o Mini', 'Fast and affordable GPT-4 model', '["chat", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, FALSE),
('openai', 'gpt-4-turbo', 'GPT-4 Turbo', 'GPT-4 Turbo with 128k context', '["chat", "vision", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, TRUE),
('openai', 'gpt-3.5-turbo', 'GPT-3.5 Turbo', 'Fast and efficient model', '["chat", "function_calling", "streaming"]', 16385, 4096, TRUE, TRUE, FALSE),
('openai', 'o1-preview', 'O1 Preview', 'Advanced reasoning model', '["chat", "reasoning"]', 128000, 32768, TRUE, FALSE, FALSE),
('openai', 'o1-mini', 'O1 Mini', 'Smaller reasoning model', '["chat", "reasoning"]', 128000, 65536, TRUE, FALSE, FALSE),
-- Anthropic Models
('anthropic', 'claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet', 'Best balance of speed and intelligence', '["chat", "vision", "function_calling", "streaming"]', 200000, 8192, TRUE, TRUE, TRUE),
('anthropic', 'claude-3-opus-20240229', 'Claude 3 Opus', 'Most capable Claude model', '["chat", "vision", "function_calling", "streaming"]', 200000, 4096, TRUE, TRUE, TRUE),
('anthropic', 'claude-3-sonnet-20240229', 'Claude 3 Sonnet', 'Balanced performance', '["chat", "vision", "function_calling", "streaming"]', 200000, 4096, TRUE, TRUE, TRUE),
('anthropic', 'claude-3-haiku-20240307', 'Claude 3 Haiku', 'Fastest Claude model', '["chat", "vision", "function_calling", "streaming"]', 200000, 4096, TRUE, TRUE, TRUE),
-- Google Models
('google', 'gemini-2.0-flash', 'Gemini 2.0 Flash', 'Google''s latest fast model', '["chat", "vision", "function_calling", "streaming"]', 1000000, 8192, TRUE, TRUE, TRUE),
('google', 'gemini-1.5-pro', 'Gemini 1.5 Pro', 'Google''s most capable model', '["chat", "vision", "function_calling", "streaming"]', 2000000, 8192, TRUE, TRUE, TRUE),
('google', 'gemini-1.5-flash', 'Gemini 1.5 Flash', 'Fast and efficient Gemini', '["chat", "vision", "function_calling", "streaming"]', 1000000, 8192, TRUE, TRUE, TRUE),
-- Groq Models
('groq', 'llama-3.3-70b-versatile', 'Llama 3.3 70B', 'Meta Llama 3.3 on Groq', '["chat", "function_calling", "streaming"]', 128000, 32768, TRUE, TRUE, FALSE),
('groq', 'llama-3.1-8b-instant', 'Llama 3.1 8B', 'Fast Llama model', '["chat", "streaming"]', 131072, 8192, TRUE, FALSE, FALSE),
('groq', 'mixtral-8x7b-32768', 'Mixtral 8x7B', 'Mixture of experts model', '["chat", "streaming"]', 32768, 32768, TRUE, FALSE, FALSE),
-- Mistral Models
('mistral', 'mistral-large-latest', 'Mistral Large', 'Most capable Mistral model', '["chat", "function_calling", "streaming"]', 128000, 4096, TRUE, TRUE, FALSE),
('mistral', 'mistral-medium-latest', 'Mistral Medium', 'Balanced Mistral model', '["chat", "function_calling", "streaming"]', 32000, 4096, TRUE, TRUE, FALSE),
('mistral', 'mistral-small-latest', 'Mistral Small', 'Fast Mistral model', '["chat", "streaming"]', 32000, 4096, TRUE, FALSE, FALSE),
-- Together AI Models
('together', 'meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo', 'Llama 3.1 70B Turbo', 'Fast Llama 70B on Together', '["chat", "function_calling", "streaming"]', 131072, 4096, TRUE, TRUE, FALSE),
('together', 'Qwen/Qwen2.5-72B-Instruct-Turbo', 'Qwen 2.5 72B', 'Alibaba Qwen model', '["chat", "function_calling", "streaming"]', 32768, 4096, TRUE, TRUE, FALSE),
-- Cohere Models
('cohere', 'command-r-plus', 'Command R+', 'Cohere''s most capable model', '["chat", "function_calling", "streaming", "rag"]', 128000, 4096, TRUE, TRUE, FALSE),
('cohere', 'command-r', 'Command R', 'Balanced Cohere model', '["chat", "function_calling", "streaming", "rag"]', 128000, 4096, TRUE, TRUE, FALSE)
ON CONFLICT DO NOTHING;

-- Add api_key_id column to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL;
