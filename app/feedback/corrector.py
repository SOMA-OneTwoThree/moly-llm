"""교정(/feedback) — 세션 대화에서 사용자 영어를 원어민 관점으로 교정.

비스트리밍 1회 + structured output(json_schema)로 항상 일관된 구조 보장.
억지 교정 금지(정말 필요할 때만), 한국어 설명, 이모지 없음 — 정책은 prompts.py.
"""
import json
from functools import lru_cache

from app.config import settings
from app.feedback.prompts import CORRECTION_SYSTEM
from app.schemas.chat import ChatMessage
from app.schemas.feedback import FeedbackResponse

# 출력 템플릿 강제(총평·이모지 없음 — 교정 항목만).
CORRECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "has_corrections": {"type": "boolean"},
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "original": {"type": "string"},
                    "corrected": {"type": "string"},
                    "explanation": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["grammar", "vocabulary", "naturalness"],
                    },
                },
                "required": ["original", "corrected", "explanation", "type"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["has_corrections", "corrections"],
    "additionalProperties": False,
}


class FeedbackCorrector:
    def __init__(self, api_key: str, model: str, max_tokens: int = 2000) -> None:
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    async def correct(self, messages: list[ChatMessage]) -> FeedbackResponse:
        convo = "\n".join(f"{m.role}: {m.content}" for m in messages)
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=CORRECTION_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": f"Conversation:\n{convo}\n\nGive correction feedback on the user's English.",
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": CORRECTION_SCHEMA}},
        )
        text = next(b.text for b in response.content if b.type == "text")
        return FeedbackResponse(**json.loads(text))


@lru_cache
def get_feedback_corrector() -> FeedbackCorrector:
    return FeedbackCorrector(
        api_key=settings.anthropic_api_key,
        model=settings.feedback_model,
        max_tokens=settings.feedback_max_tokens,
    )
