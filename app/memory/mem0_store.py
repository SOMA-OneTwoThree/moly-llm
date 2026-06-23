from app.memory.models import Memory
from app.memory.service import MemoryStore
from app.schemas.chat import ChatMessage


class Mem0MemoryStore(MemoryStore):
    def __init__(self, client) -> None:
        self.client = client

    async def search(self, user_id: str, query: str, limit: int) -> list[Memory]:
        results = await self.client.search(
            query,
            filters={"user_id": user_id},
            top_k=limit,
        )
        if isinstance(results, dict):
            results = results.get("results", [])

        return [memory_from_result(result) for result in results]

    async def save_conversation(
        self,
        user_id: str,
        messages: list[ChatMessage],
        assistant_reply: str,
    ) -> None:
        conversation = [
            message.model_dump()
            for message in messages
        ]
        if assistant_reply.strip():
            conversation.append({"role": "assistant", "content": assistant_reply})

        if conversation:
            await self.client.add(conversation, user_id=user_id)


def memory_from_result(result) -> Memory:
    if isinstance(result, str):
        return Memory(content=result)

    if isinstance(result, dict):
        content = result.get("memory") or result.get("content") or result.get("text") or ""
        score = result.get("score") or result.get("similarity")
        return Memory(content=content, score=score)

    content = getattr(result, "memory", None) or getattr(result, "content", None) or str(result)
    score = getattr(result, "score", None) or getattr(result, "similarity", None)
    return Memory(content=content, score=score)
