from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.chat.prompts import DEFAULT_SYSTEM_PROMPT


class Settings(BaseSettings):
    app_name: str = "moly-llm"
    environment: str = "local"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    memory_top_k: int = 5
    memory_cache_ttl_seconds: int = 300
    supabase_db_connection_string: str = ""
    openai_api_key: str = ""
    embedder_model: str = "text-embedding-3-small"
    memory_llm_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
