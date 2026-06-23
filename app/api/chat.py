from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.chat.service import ChatService
from app.llm.factory import create_llm_provider
from app.memory.service import get_memory_service
from app.schemas.chat import ChatRequest

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    service = ChatService(
        llm_provider=create_llm_provider(),
        memory_service=get_memory_service(),
    )

    return StreamingResponse(
        service.stream_chat(request),
        headers={"Content-Type": "text/event-stream"},
    )
