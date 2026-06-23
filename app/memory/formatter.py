from app.memory.models import Memory


def format_memories(memories: list[Memory]) -> str:
    return "\n".join(f"- {memory.content}" for memory in memories)
