from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.chat.prompts import DEFAULT_SYSTEM_PROMPT


class Settings(BaseSettings):
    app_name: str = "moly-llm"
    environment: str = "local"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    # LLM 프로바이더 선택: "anthropic"(기본, Sonnet 4.6) | "groq"(레거시)
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 1024  # 컴패니언 응답은 짧음(음성 1~3문장)
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"  # groq 사용 시
    memory_top_k: int = 5
    memory_cache_ttl_seconds: int = 300
    memory_save_every_n_turns: int = 5
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
