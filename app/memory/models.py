from dataclasses import dataclass


@dataclass(frozen=True)
class Memory:
    content: str
    score: float | None = None


@dataclass(frozen=True)
class MemoryWrite:
    content: str
