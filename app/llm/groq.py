from collections.abc import AsyncIterator

from app.llm.base import LLMMessage, StreamingLLMProvider


class GroqStreamingLLMProvider(StreamingLLMProvider):
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str, model: str) -> None:
        from openai import AsyncOpenAI

        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL)

    async def stream_chat(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
