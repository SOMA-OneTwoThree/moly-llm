from collections.abc import AsyncIterator

from app.chat.prompt_builder import PromptBuilder
from app.llm.base import StreamingLLMProvider
from app.schemas.chat import ChatRequest
from app.schemas.sse import SseDeltaEvent, SseDoneEvent


def format_sse_event(event: SseDeltaEvent | SseDoneEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


class ChatService:
    """순수 추론 — mem0 호출 0. 메모리는 요청(request.memory)으로 받는다(무상태)."""

    def __init__(
        self,
        llm_provider: StreamingLLMProvider,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.prompt_builder = prompt_builder or PromptBuilder()

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        messages = self.prompt_builder.build(request.messages, memory=request.memory)

        reply_parts: list[str] = []
        async for delta in self.llm_provider.stream_chat(messages):
            reply_parts.append(delta)
            yield format_sse_event(SseDeltaEvent(delta=delta))

        reply = "".join(reply_parts)
        yield format_sse_event(
            SseDoneEvent(reply=reply, usage={"model": self.llm_provider.model})
        )
