from collections.abc import AsyncIterator
from typing import Literal, Protocol, TypedDict


class LLMMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class StreamingLLMProvider(Protocol):
    model: str

    def stream_chat(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        pass
