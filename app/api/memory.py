import logging

from fastapi import APIRouter, HTTPException

from app.memory.service import get_memory_service
from app.schemas.memory import (
    MemoryCommitRequest,
    MemoryCommitResponse,
    MemoryLoadRequest,
    MemoryLoadResponse,
)

router = APIRouter(prefix="/memory", tags=["memory"])
_log = logging.getLogger("moly-llm")


@router.post("/load", response_model=MemoryLoadResponse)
async def load_memory(request: MemoryLoadRequest) -> MemoryLoadResponse:
    """세션시작: 사용자 장기기억 로드·랭킹·렌더 → 텍스트."""
    service = get_memory_service()
    memory_text = await service.load_for_session(request.user_id)
    return MemoryLoadResponse(memory_text=memory_text)


@router.post("/commit", response_model=MemoryCommitResponse)
async def commit_memory(request: MemoryCommitRequest) -> MemoryCommitResponse:
    """세션종료: transcript→mem0 커밋. 동기 실행 — 실패를 호출자(게이트웨이)에 그대로 반환해
    조용히 묻히지 않게 한다(이전엔 background+202라 mem0 add 실패가 완전 침묵)."""
    service = get_memory_service()
    try:
        await service.commit_session(
            user_id=request.user_id, messages=request.messages
        )
    except Exception as e:  # noqa: BLE001
        _log.exception(
            "[memory commit] mem0 add 실패 user=%s msgs=%d",
            request.user_id, len(request.messages),
        )
        raise HTTPException(status_code=500, detail=f"memory commit failed: {e!r}")
    return MemoryCommitResponse(status="committed")
