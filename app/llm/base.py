from collections.abc import AsyncIterator
from typing import Protocol

from app.schemas.chat import ChatMessage


class StreamingLLMProvider(Protocol):
    model: str

    def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        pass
