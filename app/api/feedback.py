from fastapi import APIRouter

from app.feedback.corrector import get_feedback_corrector
from app.schemas.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest) -> FeedbackResponse:
    """세션 대화 → 사용자 영어 교정(원어민 관점, 한국어 설명). 비스트리밍."""
    return await get_feedback_corrector().correct(request.messages)
