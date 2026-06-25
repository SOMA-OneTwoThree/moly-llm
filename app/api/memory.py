from fastapi import APIRouter, BackgroundTasks

from app.memory.service import get_memory_service
from app.schemas.memory import (
    MemoryCommitRequest,
    MemoryCommitResponse,
    MemoryLoadRequest,
    MemoryLoadResponse,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/load", response_model=MemoryLoadResponse)
async def load_memory(request: MemoryLoadRequest) -> MemoryLoadResponse:
    """세션시작: 사용자 장기기억 로드·랭킹·렌더 → 텍스트."""
    service = get_memory_service()
    memory_text = await service.load_for_session(request.user_id)
    return MemoryLoadResponse(memory_text=memory_text)


@router.post("/commit", response_model=MemoryCommitResponse)
async def commit_memory(
    request: MemoryCommitRequest, background_tasks: BackgroundTasks
) -> MemoryCommitResponse:
    """세션종료: transcript→mem0 커밋. 추출이 느려 백그라운드로(202 즉시 반환)."""
    service = get_memory_service()
    background_tasks.add_task(
        service.commit_session, user_id=request.user_id, messages=request.messages
    )
    return MemoryCommitResponse(status="accepted")
