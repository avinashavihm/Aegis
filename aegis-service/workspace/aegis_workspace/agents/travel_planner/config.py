import os
from dataclasses import dataclass

@dataclass
class Config:
    """
    Configuration class for the Travel Planner Agent.
    """
    openai_api_key: str = os.environ.get("OPENAI_API_KEY")
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY")
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    groq_api_key: str = os.environ.get("GROQ_API_KEY")
    mistral_api_key: str = os.environ.get("MISTRAL_API_KEY")
    cohere_api_key: str = os.environ.get("COHERE_API_KEY")
    together_api_key: str = os.environ.get("TOGETHER_API_KEY")
    serpapi_api_key: str = os.environ.get("SERPAPI_API_KEY")
    google_maps_api_key: str = os.environ.get("GOOGLE_MAPS_API_KEY")

    default_llm_model: str = os.environ.get("DEFAULT_LLM_MODEL") or "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2000

    def __post_init__(self):
        """
        Validate that required environment variables are set.
        """
        # Choose the first available provider; fall back to default model
        available = [
            ("openai", self.openai_api_key, "gpt-4o"),
            ("anthropic", self.anthropic_api_key, "claude-3-opus-20240229"),
            ("gemini", self.gemini_api_key, "gemini-1.5-pro"),
            ("groq", self.groq_api_key, "llama-3-70b"),
            ("mistral", self.mistral_api_key, "mistral-large-latest"),
            ("cohere", self.cohere_api_key, "command-r-plus"),
            ("together", self.together_api_key, "meta-llama/Meta-Llama-3-70B-Instruct-Turbo"),
        ]

        for provider, key, suggested_model in available:
            if key:
                self.default_llm_model = suggested_model
                break
        else:
            print("Warning: No LLM API keys found in environment. LLM calls will fail until a key is set.")

        if not self.serpapi_api_key:
            print("Warning: SERPAPI_API_KEY environment variable not set. Search functionality will be limited.")

        if not self.google_maps_api_key:
            print("Warning: GOOGLE_MAPS_API_KEY environment variable not set. Distance calculations will be limited.")