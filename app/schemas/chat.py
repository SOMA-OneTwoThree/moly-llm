from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    # 세션시작 /memory/load에서 받아 클라가 캐싱 → 매 턴 동일하게 전달(무상태).
    # 옵션(default "") — 게이트웨이 미연동 시에도 /chat 안 깨짐(메모리만 빔).
    memory: str = ""
