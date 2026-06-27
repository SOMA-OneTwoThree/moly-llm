"""D1 검증 — moly-llm 내부 호출 인증(공유 시크릿).

- 토큰 미설정(로컬): 모든 라우트 통과(미강제)
- 토큰 설정(프로덕션): /health는 공개, 보호 라우트는 헤더 없으면 401, 맞으면 통과(401 아님)
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "x")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

# raise_server_exceptions=False: 인증 통과 후 라우트가 DB 없어 500 나도 re-raise 말고 응답으로.
# (우리가 검증할 건 "401이냐 아니냐" = 인증 동작뿐)
client = TestClient(app, raise_server_exceptions=False)
results = []


def check(name, cond):
    results.append((name, cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")


def run():
    SECRET = "shared-secret-xyz"

    # ── 토큰 설정(프로덕션 모드) ──
    settings.internal_service_token = SECRET

    # /health는 토큰 없이도 공개
    check("health 공개(토큰 무관)", client.get("/health").status_code == 200)

    # 보호 라우트: 헤더 없음 → 401
    r = client.post("/memory/load", json={"user_id": "u1"})
    check("토큰 설정+헤더없음 → 401", r.status_code == 401)

    # 보호 라우트: 잘못된 헤더 → 401
    r = client.post("/memory/load", json={"user_id": "u1"},
                    headers={"X-Internal-Token": "wrong"})
    check("잘못된 토큰 → 401", r.status_code == 401)

    # 보호 라우트: 올바른 헤더 → 인증 통과(401 아님; 이후 DB 없어 다른 에러는 무방)
    r = client.post("/memory/load", json={"user_id": "u1"},
                    headers={"X-Internal-Token": SECRET})
    check("올바른 토큰 → 인증 통과(401 아님)", r.status_code != 401)

    # ── 토큰 미설정(로컬 모드) → 미강제 ──
    settings.internal_service_token = ""
    r = client.post("/memory/load", json={"user_id": "u1"})  # 헤더 없음
    check("토큰 미설정 → 미강제(401 아님)", r.status_code != 401)

    print()
    passed = sum(1 for _, c in results if c)
    print(f"=== {passed}/{len(results)} PASS ===")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
