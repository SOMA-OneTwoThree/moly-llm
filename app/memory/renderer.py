"""ScoredMemory → system 프롬프트용 텍스트 (순수).

ACTIVE/PASSIVE 그룹으로 라벨링 + 상대시간("today"/"yesterday"/"N days ago").
상대시간은 LOAD 시점 now로 1회 계산해 고정(매 턴 재계산 금지 → 캐시 적중 유지).
prompt 구조(어디 넣을지·cache_control)는 PromptBuilder 책임, 여기선 도메인 텍스트만.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.memory.models import ScoredMemory, Tier
from app.memory.retention import _age_days

_ACTIVE_HEADER = "[Recent — you may bring these up naturally]"
_PASSIVE_HEADER = "[Background — do not bring up first; use only if relevant]"


def _relative_label(age_days: float | None) -> str:
    if age_days is None:
        return ""
    days = int(age_days)
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def _line(scored: ScoredMemory, now: datetime) -> str:
    ts = scored.memory.updated_at or scored.memory.created_at
    label = _relative_label(_age_days(ts, now))
    return f"- {label}: {scored.memory.content}" if label else f"- {scored.memory.content}"


def render_memories(scored: list[ScoredMemory], now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)

    active = [s for s in scored if s.tier == Tier.ACTIVE]
    passive = [s for s in scored if s.tier == Tier.PASSIVE]

    blocks: list[str] = []
    if active:
        blocks.append(_ACTIVE_HEADER)
        blocks.extend(_line(s, now) for s in active)
    if passive:
        if blocks:
            blocks.append("")
        blocks.append(_PASSIVE_HEADER)
        blocks.extend(f"- {s.memory.content}" for s in passive)

    return "\n".join(blocks)
