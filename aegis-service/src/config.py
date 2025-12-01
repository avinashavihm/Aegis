import os
from typing import Optional


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


settings = Settings()
