from app.config import settings
from app.chat.prompts import DEFAULT_SYSTEM_PROMPT
from app.llm.base import LLMMessage
from app.schemas.chat import ChatMessage


class PromptBuilder:
    def __init__(self, system_prompt: str | None = None) -> None:
        self.system_prompt = system_prompt or settings.system_prompt or DEFAULT_SYSTEM_PROMPT

    def build(
        self,
        messages: list[ChatMessage],
        memory: str = "",
    ) -> list[LLMMessage]:
        final_messages: list[LLMMessage] = [
            {"role": "system", "content": self.system_prompt}
        ]

        memory = memory.strip()
        if memory:
            final_messages.append(
                {"role": "system", "content": f"Relevant user memory:\n{memory}"}
            )

        final_messages.extend(
            {"role": message.role, "content": message.content} for message in messages
        )
        return final_messages
