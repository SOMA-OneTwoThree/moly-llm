import os
from functools import lru_cache

# mem0 텔레메트리(phone-home) 비활성 — mem0 get_all/add는 매 호출 capture_event/notice로
# 외부 분석 엔드포인트에 네트워크 호출을 한다. 이게 세션시작 load의 간헐적 지연(ReadTimeout)
# 주요 원인. mem0 임포트 전에 env로 꺼야 적용됨(telemetry 모듈이 임포트 시 1회 읽음).
# infra가 명시 설정하면 그 값 우선(setdefault).
os.environ.setdefault("MEM0_TELEMETRY", "False")

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.chat.prompts import DEFAULT_SYSTEM_PROMPT


class MemoryConfig(BaseModel):
    """장기기억 로드/감쇠 정책 노브 (전부 설정, 로직에 하드코딩 금지).

    env override: MEMORY__HALF_LIFE_DAYS=14 식 (이중 언더스코어).
    """

    # 세션시작 로드 시 mem0에서 가져올 상한(전부 가져와 로컬 랭킹 — get_all이 recency순이 아니라서).
    load_top_k: int = 500
    # 감쇠 반감기(일). recency = 0.5^(age/half_life). Stage A는 타입 무관 단일값.
    half_life_days: float = 10.0
    # 이 나이(일) 이내 = ACTIVE(먼저 꺼내도 됨). 초과 = PASSIVE(관련될 때만).
    active_days: float = 3.0
    # 렌더에 넣을 최대 항목 수(토큰예산 근사). 초과분은 recency 낮은 순으로 컷.
    max_render_items: int = 20


class Settings(BaseSettings):
    app_name: str = "moly-llm"
    environment: str = "local"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    # LLM 프로바이더 선택: "anthropic"(기본, Sonnet 4.6) | "groq"(레거시)
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 1024  # 컴패니언 응답은 짧음(음성 1~3문장)
    # 교정(/feedback) — 비스트리밍 1회 + 구조화 출력. 품질 위해 Sonnet/Opus.
    feedback_model: str = "claude-sonnet-4-6"
    feedback_max_tokens: int = 2000
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"  # groq 사용 시
    # 내부 호출 보호용 공유 시크릿(게이트웨이만 호출). 비어있으면 미강제(로컬).
    # 게이트웨이 INTERNAL_SERVICE_TOKEN과 동일값(Parameter Store).
    internal_service_token: str = ""
    # mem0(장기기억) — 데이터는 우리 Supabase, 추출/임베딩은 OpenAI
    supabase_db_connection_string: str = ""
    openai_api_key: str = ""
    embedder_model: str = "text-embedding-3-small"
    memory_llm_model: str = "gpt-4.1-mini"
    memory: MemoryConfig = MemoryConfig()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
