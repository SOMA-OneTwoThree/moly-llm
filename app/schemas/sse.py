from typing import Any, Literal

from pydantic import BaseModel, Field


class SseDeltaEvent(BaseModel):
    type: Literal["delta"] = "delta"
    delta: str


class SseDoneEvent(BaseModel):
    type: Literal["done"] = "done"
    reply: str
    usage: dict[str, Any] = Field(default_factory=dict)


class SseErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


SseEvent = SseDeltaEvent | SseDoneEvent | SseErrorEvent
