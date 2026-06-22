"""moly-llm — Molly의 뇌 (LLM 서비스).

POST /chat {messages:[{role,content}], user_id?} → SSE delta 스트림.
- system(페르소나 + Mem0 기억)은 서버 소유, 클라(게이트웨이)는 user/assistant 턴만 전송.
- userId 있으면 Mem0에서 관련 기억을 캐시 우선 조회해 system에 주입.
- 응답 후 백그라운드로 Mem0 적재(async).

스캐폴드: 엔드포인트 골격만. 실제 구현은 chat/llm/memory 모듈에 채운다.
참고: moly-pipeline-test 의 src/lib/{llm,chat,memory} (Node) 를 포팅.
"""
from fastapi import FastAPI

app = FastAPI(title="moly-llm")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "moly-llm"}


# TODO(포팅):
# from fastapi import Request
# from sse_starlette.sse import EventSourceResponse
# from .chat.service import generate_reply_stream
#
# @app.post("/chat")
# async def chat(req: Request):
#     body = await req.json()
#     messages = body.get("messages") or [{"role": "user", "content": body["text"]}]
#     user_id = body.get("user_id")
#     return EventSourceResponse(generate_reply_stream(messages, user_id=user_id))
