from collections.abc import AsyncIterator

from app.chat.prompt_builder import PromptBuilder
from app.llm.base import StreamingLLMProvider
from app.memory.formatter import format_memories
from app.memory.service import MemoryService
from app.schemas.chat import ChatRequest
from app.schemas.sse import SseDeltaEvent, SseDoneEvent


def format_sse_event(event: SseDeltaEvent | SseDoneEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


class ChatService:
    def __init__(
        self,
        llm_provider: StreamingLLMProvider,
        memory_service: MemoryService | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.memory_service = memory_service or MemoryService()
        self.prompt_builder = prompt_builder or PromptBuilder()

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        reply_parts = []
        memories = await self.memory_service.search(
            user_id=request.user_id,
            query=self._memory_query(request),
        )
        messages = self.prompt_builder.build(
            request.messages,
            memory=format_memories(memories),
        )

        async for delta in self.llm_provider.stream_chat(messages):
            reply_parts.append(delta)
            yield format_sse_event(SseDeltaEvent(delta=delta))

        reply = "".join(reply_parts)
        yield format_sse_event(
            SseDoneEvent(reply=reply, usage={"model": self.llm_provider.model})
        )

    def _memory_query(self, request: ChatRequest) -> str:
        return request.messages[-1].content
