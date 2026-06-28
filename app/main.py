import logging

from fastapi import Depends, FastAPI

# 앱 로거 INFO 출력 — uvicorn 기본은 app 로거(moly-llm)를 INFO로 안 띄워 _log.info가 묻힌다.
# 메모리 로드 소요시간 등 진단 로그가 컨테이너 stdout에 찍히게 한다.
logging.basicConfig(level=logging.INFO)
logging.getLogger("moly-llm").setLevel(logging.INFO)

from app.api.chat import router as chat_router
from app.api.deps import verify_internal_token
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.memory import router as memory_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    # /health는 공개(헬스체크). 나머지는 내부 토큰 검증(심층방어, D1).
    internal = [Depends(verify_internal_token)]
    app.include_router(health_router)
    app.include_router(chat_router, dependencies=internal)
    app.include_router(memory_router, dependencies=internal)
    app.include_router(feedback_router, dependencies=internal)
    return app


app = create_app()
