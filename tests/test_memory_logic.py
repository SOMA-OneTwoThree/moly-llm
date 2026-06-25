"""retention/renderer 순수 로직 단위테스트 (DB·LLM 호출 없음).

pytest 있으면 `pytest`, 없으면 `python tests/test_memory_logic.py`로 실행.
"""
from datetime import datetime, timedelta, timezone

from app.config import MemoryConfig
from app.memory.models import Memory, Tier
from app.memory.renderer import render_memories
from app.memory.retention import recency_factor, score_memories

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)


def _mem(content, age_days=None, **kw):
    ts = None if age_days is None else NOW - timedelta(days=age_days)
    return Memory(content=content, created_at=ts, updated_at=ts, **kw)


def test_recency_factor():
    assert recency_factor(0, 10) == 1.0
    assert recency_factor(10, 10) == 0.5  # 반감기
    assert recency_factor(20, 10) == 0.25
    assert recency_factor(5, 0) == 1.0  # half_life<=0 → 감쇠 없음


def test_tier_boundary_active_3d():
    cfg = MemoryConfig(active_days=3.0, half_life_days=10.0)
    scored = score_memories(
        [_mem("today", 0), _mem("3d", 3), _mem("4d", 4)], cfg, now=NOW
    )
    by = {s.memory.content: s.tier for s in scored}
    assert by["today"] == Tier.ACTIVE
    assert by["3d"] == Tier.ACTIVE       # 경계 포함(age<=3)
    assert by["4d"] == Tier.PASSIVE


def test_ranking_by_recency_desc():
    cfg = MemoryConfig(half_life_days=10.0)
    scored = score_memories([_mem("old", 30), _mem("fresh", 1), _mem("mid", 7)], cfg, now=NOW)
    assert [s.memory.content for s in scored] == ["fresh", "mid", "old"]


def test_max_render_items_cap():
    cfg = MemoryConfig(max_render_items=2)
    scored = score_memories([_mem(f"m{i}", i) for i in range(10)], cfg, now=NOW)
    assert len(scored) == 2
    assert [s.memory.content for s in scored] == ["m0", "m1"]  # 가장 신선한 2개


def test_missing_timestamp_is_fresh_passive():
    cfg = MemoryConfig()
    scored = score_memories([_mem("no-ts", None)], cfg, now=NOW)
    assert scored[0].recency == 1.0
    assert scored[0].tier == Tier.PASSIVE


def test_naive_timestamp_treated_as_utc():
    cfg = MemoryConfig(active_days=3.0)
    naive = Memory(content="naive", created_at=NOW.replace(tzinfo=None) - timedelta(days=1))
    scored = score_memories([naive], cfg, now=NOW)
    assert scored[0].tier == Tier.ACTIVE  # 1일 전 → ACTIVE (tz 처리됨)


def test_render_groups_and_relative_time():
    cfg = MemoryConfig(active_days=3.0, half_life_days=10.0)
    mems = [_mem("exam", 1), _mem("trip planning", 0), _mem("from Busan", 40)]
    text = render_memories(score_memories(mems, cfg, now=NOW), now=NOW)
    assert "[Recent" in text and "[Background" in text
    assert "- yesterday: exam" in text
    assert "- today: trip planning" in text
    # PASSIVE는 상대시간 없이 내용만
    assert "- from Busan" in text
    # ACTIVE가 Background보다 위
    assert text.index("[Recent") < text.index("[Background")


def test_render_empty():
    assert render_memories([], now=NOW) == ""


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok: {t.__name__}")
    print(f"\nALL {len(tests)} TESTS PASSED ✅")


if __name__ == "__main__":
    _run()
