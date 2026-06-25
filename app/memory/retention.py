"""메모리 보존 정책 — 순수 로직(I/O 없음, DB 모름 → 단위테스트 가능).

Stage A: recency만으로 랭킹 + ACTIVE/PASSIVE 2등급. 타입/중요도 없음.
감쇠는 created_at 기반(mem0 async add가 updated_at을 재언급에 안 바꿔서 강화 미작동 — 검증됨).
DORMANT 티어 없음(드롭하면 LLM이 못 봐서 부활 불가 — 검증됨). 전부 로드, recency로 랭킹.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.config import MemoryConfig
from app.memory.models import Memory, ScoredMemory, Tier


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)


def _age_days(ts: datetime | None, now: datetime) -> float | None:
    if ts is None:
        return None
    return max(0.0, (now - _as_utc(ts)).total_seconds() / 86400.0)


def recency_factor(age_days: float, half_life_days: float) -> float:
    """0.5^(age/half_life). half_life<=0이면 감쇠 안 함(1.0)."""
    if half_life_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def score_memories(
    memories: list[Memory],
    config: MemoryConfig,
    now: datetime | None = None,
) -> list[ScoredMemory]:
    """기억들에 recency·tier 부여 → recency 내림차순 정렬 → 상한 컷."""
    now = now or datetime.now(timezone.utc)

    scored: list[ScoredMemory] = []
    for memory in memories:
        age = _age_days(memory.updated_at or memory.created_at, now)
        if age is None:
            # 타임스탬프 없음 → 신선한 것으로 취급(불이익 금지), PASSIVE
            scored.append(ScoredMemory(memory=memory, recency=1.0, tier=Tier.PASSIVE))
            continue

        recency = recency_factor(age, config.half_life_days)
        tier = Tier.ACTIVE if age <= config.active_days else Tier.PASSIVE
        scored.append(ScoredMemory(memory=memory, recency=recency, tier=tier))

    scored.sort(key=lambda s: s.recency, reverse=True)
    return scored[: config.max_render_items]
