"""mem0(AsyncMemory) ↔ 도메인 어댑터. mem0 형식은 여기에만 갇힌다.

LOAD = get_all(filters={user_id}) — get_all은 zero-vector 코사인+top_k라 recency순이 아니므로
       load_top_k를 충분히 크게(전부) 가져와 retention이 로컬 랭킹한다(검증된 제약).
COMMIT = add(transcript, infer=True) — mem0가 OpenAI로 추출·해시중복스킵(additive-only).
"""
from __future__ import annotations

from datetime import datetime

from app.memory.models import Memory
from app.memory.service import MemoryStore
from app.schemas.chat import ChatMessage


class Mem0MemoryStore(MemoryStore):
    def __init__(self, client) -> None:
        self.client = client

    async def get_all(self, user_id: str, limit: int) -> list[Memory]:
        results = await self.client.get_all(filters={"user_id": user_id}, top_k=limit)
        if isinstance(results, dict):
            results = results.get("results", [])
        return [memory_from_result(result) for result in results]

    async def add(self, user_id: str, messages: list[ChatMessage]) -> None:
        conversation = [message.model_dump() for message in messages]
        if conversation:
            await self.client.add(conversation, user_id=user_id)


def _parse_dt(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def memory_from_result(result) -> Memory:
    if isinstance(result, str):
        return Memory(content=result)

    if isinstance(result, dict):
        get = result.get
    else:  # 객체 형태 fallback
        def get(key, default=None):
            return getattr(result, key, default)

    content = get("memory") or get("content") or get("text") or ""
    return Memory(
        content=content,
        id=get("id"),
        created_at=_parse_dt(get("created_at")),
        updated_at=_parse_dt(get("updated_at")),
        score=get("score") or get("similarity"),
        metadata=get("metadata") or {},
    )
