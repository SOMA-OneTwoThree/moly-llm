from dataclasses import dataclass
from time import monotonic

from app.memory.models import Memory


@dataclass
class MemoryCacheEntry:
    memories: list[Memory]
    expires_at: float


class MemoryCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[tuple[str, str], MemoryCacheEntry] = {}

    def get(self, user_id: str, query: str) -> list[Memory] | None:
        key = (user_id, query)
        entry = self._entries.get(key)
        if entry is None:
            return None

        if entry.expires_at <= monotonic():
            self._entries.pop(key, None)
            return None

        return entry.memories

    def set(self, user_id: str, query: str, memories: list[Memory]) -> None:
        self._entries[(user_id, query)] = MemoryCacheEntry(
            memories=memories,
            expires_at=monotonic() + self.ttl_seconds,
        )
