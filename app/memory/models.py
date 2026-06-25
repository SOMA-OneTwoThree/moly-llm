from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass(frozen=True)
class Memory:
    """장기기억 한 건 (도메인 타입 — mem0 형식 모름)."""

    content: str
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    score: float | None = None  # mem0 검색 점수(있으면)
    metadata: dict = field(default_factory=dict)


class Tier(str, Enum):
    """행동 권한 등급."""

    ACTIVE = "active"  # 먼저 꺼내도 됨
    PASSIVE = "passive"  # 관련될 때만


@dataclass(frozen=True)
class ScoredMemory:
    """retention 정책 출력 — 원본 + 신선도 + 등급."""

    memory: Memory
    recency: float  # 0~1, 랭킹/렌더순서 결정
    tier: Tier
