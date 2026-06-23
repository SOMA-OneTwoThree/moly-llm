from functools import lru_cache
from typing import Protocol

from app.config import settings
from app.memory.cache import MemoryCache
from app.memory.models import Memory
from app.schemas.chat import ChatMessage


class MemoryStore(Protocol):
    async def search(self, user_id: str, query: str, limit: int) -> list[Memory]:
        ...

    async def save_conversation(
        self,
        user_id: str,
        messages: list[ChatMessage],
        assistant_reply: str,
    ) -> None:
        ...


class MemoryService:
    def __init__(
        self,
        store: MemoryStore | None = None,
        top_k: int = settings.memory_top_k,
        cache_ttl_seconds: int = settings.memory_cache_ttl_seconds,
    ) -> None:
        if store is None:
            raise ValueError("MemoryService requires a MemoryStore.")

        self.store = store
        self.top_k = top_k
        self.cache = MemoryCache(ttl_seconds=cache_ttl_seconds)

    async def search(self, user_id: str, query: str) -> list[Memory]:
        cached_memories = self.cache.get(user_id, query)
        if cached_memories is not None:
            return cached_memories

        memories = await self.store.search(user_id, query, limit=self.top_k)
        self.cache.set(user_id, query, memories)
        return memories

    async def remember_from_conversation(
        self,
        user_id: str,
        messages: list[ChatMessage],
        assistant_reply: str,
    ) -> None:
        await self.store.save_conversation(user_id, messages, assistant_reply)


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
