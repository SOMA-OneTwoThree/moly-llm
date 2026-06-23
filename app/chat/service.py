from collections.abc import AsyncIterator
from typing import Protocol

from app.chat.prompt_builder import PromptBuilder
from app.config import settings
from app.llm.base import StreamingLLMProvider
from app.memory.formatter import format_memories
from app.memory.service import MemoryService
from app.schemas.chat import ChatRequest
from app.schemas.sse import SseDeltaEvent, SseDoneEvent


class BackgroundTaskCollector(Protocol):
    def add_task(self, func, *args, **kwargs) -> None:
        ...


def format_sse_event(event: SseDeltaEvent | SseDoneEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


class ChatService:
    def __init__(
        self,
        llm_provider: StreamingLLMProvider,
        memory_service: MemoryService | None = None,
        prompt_builder: PromptBuilder | None = None,
        memory_save_every_n_turns: int = settings.memory_save_every_n_turns,
    ) -> None:
        self.llm_provider = llm_provider
        self.memory_service = memory_service or MemoryService()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.memory_save_every_n_turns = memory_save_every_n_turns

    async def stream_chat(
        self,
        request: ChatRequest,
        background_tasks: BackgroundTaskCollector | None = None,
    ) -> AsyncIterator[str]:
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
        if background_tasks is not None and self._should_save_memory(request):
            background_tasks.add_task(
                self.memory_service.remember_from_conversation,
                user_id=request.user_id,
                messages=self._memory_save_messages(request),
                assistant_reply=reply,
            )

    def _memory_query(self, request: ChatRequest) -> str:
        return request.messages[-1].content

    def _should_save_memory(self, request: ChatRequest) -> bool:
        if self.memory_save_every_n_turns <= 0:
            return False

        user_turns = sum(1 for message in request.messages if message.role == "user")
        return user_turns > 0 and user_turns % self.memory_save_every_n_turns == 0

    def _memory_save_messages(self, request: ChatRequest):
        user_message_indexes = [
            index
            for index, message in enumerate(request.messages)
            if message.role == "user"
        ]
        start_index = user_message_indexes[-self.memory_save_every_n_turns]
        return request.messages[start_index:]
