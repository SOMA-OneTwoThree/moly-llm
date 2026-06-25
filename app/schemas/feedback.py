from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage


class Correction(BaseModel):
    original: str  # 사용자 영어 원문
    corrected: str  # 원어민이 실제로 쓸 표현
    explanation: str  # 한국어 설명
    type: Literal["grammar", "vocabulary", "naturalness"]


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)


class FeedbackResponse(BaseModel):
    has_corrections: bool
    corrections: list[Correction] = []
