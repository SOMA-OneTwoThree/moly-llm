from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage


class MemoryLoadRequest(BaseModel):
    user_id: str = Field(min_length=1)


class MemoryLoadResponse(BaseModel):
    memory_text: str  # 렌더된 ACTIVE/PASSIVE 텍스트 (게이트웨이가 /chat의 memory로 forward)


class MemoryCommitRequest(BaseModel):
    user_id: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    # 멱등키 — 세션종료 중복 발화 방지용. Stage A는 받기만(중복추적은 server 연동 시).
    session_id: str | None = None


class MemoryCommitResponse(BaseModel):
    status: str
