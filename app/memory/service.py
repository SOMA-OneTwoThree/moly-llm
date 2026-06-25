from datetime import datetime
from functools import lru_cache
from typing import Protocol

from app.config import MemoryConfig, settings
from app.memory.models import Memory
from app.memory.renderer import render_memories
from app.memory.retention import score_memories
from app.schemas.chat import ChatMessage


class MemoryStore(Protocol):
    """영속 포트 — 구현(mem0)은 어댑터에. 테스트는 이 인터페이스를 스텁."""

    async def get_all(self, user_id: str, limit: int) -> list[Memory]:
        ...

    async def add(self, user_id: str, messages: list[ChatMessage]) -> None:
        ...


class MemoryService:
    """조립만 하는 얇은 오케스트레이터 (정책=retention, 렌더=renderer는 순수 모듈)."""

    def __init__(self, store: MemoryStore | None = None, config: MemoryConfig | None = None) -> None:
        if store is None:
            raise ValueError("MemoryService requires a MemoryStore.")
        self.store = store
        self.config = config or settings.memory

    async def load_for_session(self, user_id: str, now: datetime | None = None) -> str:
        """세션시작: 전부 로드 → recency 랭킹·tier → 렌더 텍스트(now 고정)."""
        memories = await self.store.get_all(user_id, limit=self.config.load_top_k)
        scored = score_memories(memories, self.config, now=now)
        return render_memories(scored, now=now)

    async def commit_session(self, user_id: str, messages: list[ChatMessage]) -> None:
        """세션종료: transcript를 mem0에 커밋(추출은 mem0가 수행)."""
        await self.store.add(user_id, messages)


@lru_cache
def get_memory_service() -> MemoryService:
    return MemoryService(store=create_memory_store())


def create_memory_store() -> MemoryStore:
    if not settings.supabase_db_connection_string:
        raise ValueError("SUPABASE_DB_CONNECTION_STRING is required.")

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required.")

    from app.memory.mem0_client import create_mem0_client
    from app.memory.mem0_store import Mem0MemoryStore

    return Mem0MemoryStore(
        client=create_mem0_client(
            db_connection_string=settings.supabase_db_connection_string,
            openai_api_key=settings.openai_api_key,
            memory_llm_model=settings.memory_llm_model,
            embedder_model=settings.embedder_model,
        )
    )
