import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_DIR = Path.home() / ".aegis"
CONFIG_FILE = CONFIG_DIR / "config"

def _ensure_config_dir():
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(parents=True)

def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def save_config(config: Dict[str, Any]):
    _ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f)

def get_api_url() -> str:
    """Get API base URL from config or environment."""
    config = load_config()
    return config.get("api_url", os.getenv("AEGIS_API_URL", "http://localhost:8000"))

def set_api_url(url: str):
    """Set API base URL."""
    config = load_config()
    config["api_url"] = url
    save_config(config)

def set_context(workspace_slug: str):
    """Set current workspace context."""
    config = load_config()
    config["current_context"] = workspace_slug
    save_config(config)

def get_context() -> Optional[str]:
    """Get current workspace context."""
    config = load_config()
    return config.get("current_context")

def set_auth_token(token: str):
    """Store JWT authentication token."""
    config = load_config()
    config["auth_token"] = token
    save_config(config)

def get_auth_token() -> Optional[str]:
    """Get JWT authentication token."""
    config = load_config()
    return config.get("auth_token")

def clear_auth():
    """Clear authentication token."""
    config = load_config()
    if "auth_token" in config:
        del config["auth_token"]
    save_config(config)

def set_default_output_format(format: str):
    """Set default output format."""
    config = load_config()
    config["output_format"] = format
    save_config(config)

def get_default_output_format() -> str:
    """Get default output format."""
    config = load_config()
    return config.get("output_format", "text")
