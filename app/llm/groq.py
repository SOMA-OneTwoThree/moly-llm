from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.llm.base import StreamingLLMProvider
from app.schemas.chat import ChatMessage


class GroqStreamingLLMProvider(StreamingLLMProvider):
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL)

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            stream=True,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
