import os
from typing import Optional


def str_to_bool(value) -> bool:
    """Convert string to bool"""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    true_values = {'true', 'yes', '1', 'on', 't', 'y'}
    false_values = {'false', 'no', '0', 'off', 'f', 'n'}
    value = str(value).lower().strip()
    if value in true_values:
        return True
    if value in false_values:
        return False
    return False


class Settings:
    """Simple settings class using environment variables."""
    
    def __init__(self):
        # Database
        self.db_host: str = os.getenv("DB_HOST", "localhost")
        self.db_port: int = int(os.getenv("DB_PORT", "5432"))
        self.db_name: str = os.getenv("DB_NAME", "agentic_ops")
        self.db_user: str = os.getenv("DB_USER", "admin")
        self.db_password: str = os.getenv("DB_PASSWORD", "password123")
        
        # JWT
        self.secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm: str = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # CORS
        cors_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        self.cors_origins: list = [origin.strip() for origin in cors_str.split(",")]
        
        # Aegis Agent Framework Settings
        # LLM API Keys (at least one required for agents)
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        self.huggingface_api_key: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")
        
        # Model configuration
        self.completion_model: str = os.getenv("COMPLETION_MODEL", "gemini/gemini-2.0-flash")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        # Workspace configuration
        self.workspace_dir: str = os.getenv("WORKSPACE_DIR", "workspace")
        self.local_root: str = os.getenv("LOCAL_ROOT", os.getcwd())
        
        # Debug and logging
        self.aegis_debug: bool = str_to_bool(os.getenv("AEGIS_DEBUG", False))
        self.aegis_log_path: Optional[str] = os.getenv("AEGIS_LOG_PATH")
        
        # Function calling configuration
        self.fn_call: bool = str_to_bool(os.getenv("FN_CALL", True))
        self.api_base_url: Optional[str] = os.getenv("API_BASE_URL")
        
        # Agent execution limits
        self.max_agent_turns: int = int(os.getenv("MAX_AGENT_TURNS", "10"))
        self.max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "12000"))


settings = Settings()
