from collections.abc import AsyncIterator

from app.llm.base import StreamingLLMProvider
from app.schemas.chat import ChatRequest
from app.schemas.sse import SseDeltaEvent, SseDoneEvent


def format_sse_event(event: SseDeltaEvent | SseDoneEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


class ChatService:
    def __init__(self, llm_provider: StreamingLLMProvider) -> None:
        self.llm_provider = llm_provider

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        reply_parts = []

        async for delta in self.llm_provider.stream_chat(request.messages):
            reply_parts.append(delta)
            yield format_sse_event(SseDeltaEvent(delta=delta))

        reply = "".join(reply_parts)
        yield format_sse_event(
            SseDoneEvent(reply=reply, usage={"model": self.llm_provider.model})
        )
