from functools import lru_cache
from typing import Protocol

from app.config import settings
from app.memory.cache import MemoryCache
from app.memory.models import Memory, MemoryWrite
from app.schemas.chat import ChatMessage


class MemoryStore(Protocol):
    async def search(self, user_id: str, query: str, limit: int) -> list[Memory]:
        ...

    async def save(self, user_id: str, memories: list[MemoryWrite]) -> None:
        ...


class NoopMemoryStore(MemoryStore):
    async def search(self, user_id: str, query: str, limit: int) -> list[Memory]:
        return []

    async def save(self, user_id: str, memories: list[MemoryWrite]) -> None:
        return None


class MemoryService:
    def __init__(
        self,
        store: MemoryStore | None = None,
        top_k: int = settings.memory_top_k,
        cache_ttl_seconds: int = settings.memory_cache_ttl_seconds,
    ) -> None:
        self.store = store or NoopMemoryStore()
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
        memories = await self.extract_memories(messages, assistant_reply)
        if memories:
            await self.store.save(user_id, memories)

    async def extract_memories(
        self,
        messages: list[ChatMessage],
        assistant_reply: str,
    ) -> list[MemoryWrite]:
        return []


@lru_cache
def get_memory_service() -> MemoryService:
    return MemoryService()
