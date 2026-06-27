"""내부 호출 인증 — 게이트웨이↔moly-llm 공유 시크릿(심층방어).

moly-llm은 무상태 내부 서비스라 인터넷에 직접 노출되면 안 되지만(네트워크 격리),
포트 노출/SSRF 대비 백스톱. 게이트웨이가 X-Internal-Token 헤더로 공유 시크릿을 보낸다.
settings.internal_service_token이 비어있으면 미강제(로컬 개발). /health는 적용 안 함.
"""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import settings


async def verify_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    expected = settings.internal_service_token
    if not expected:
        return  # 미설정(로컬) → 미강제
    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="unauthorized")
