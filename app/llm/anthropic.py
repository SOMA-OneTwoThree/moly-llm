"""Anthropic Claude (Sonnet 4.6) — 네이티브 SDK 스트리밍.

PromptBuilder가 만든 messages 리스트에서 system role을 추출해 top-level `system`으로 넘긴다
(Anthropic은 system을 messages 배열에 못 넣음). 메모리도 PromptBuilder가 system 메시지로
넣으므로 여기서 system에 통합된다. thinking off, max_tokens 고정.
system prefix엔 cache_control 부여(고정 prefix → 캐시 읽기 0.1×).
"""
from collections.abc import AsyncIterator

from app.llm.base import LLMMessage, StreamingLLMProvider


def _split_system_and_convo(messages: list[LLMMessage]) -> tuple[str, list[dict]]:
    """messages를 (system 텍스트, user/assistant convo)로 분리.

    system은 top-level로 합치고, convo는 user/assistant만 남긴다. Anthropic은 첫 메시지가
    user여야 하므로 선발화(AI 먼저 인사)·재연결로 history가 assistant로 시작하면 선행
    non-user 메시지를 방어적으로 절단한다.
    """
    system = "\n\n".join(
        m["content"] for m in messages if m["role"] == "system" and m["content"]
    ).strip()
    convo = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m["role"] in ("user", "assistant")
    ]
    while convo and convo[0]["role"] != "user":
        convo.pop(0)
    return system, convo


class AnthropicStreamingLLMProvider(StreamingLLMProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int = 1024) -> None:
        from anthropic import AsyncAnthropic

        self.model = model
        self.max_tokens = max_tokens
        self.client = AsyncAnthropic(api_key=api_key)

    async def stream_chat(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        # system은 top-level로, user/assistant만 convo로(첫 메시지 user 보장은 헬퍼가 처리).
        system, convo = _split_system_and_convo(messages)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": convo,
            "thinking": {"type": "disabled"},  # 컴패니언 실시간 응답 — 사고 off
        }
        if system:
            # 고정 prefix(페르소나+메모리) 캐싱 → 이후 턴 입력토큰 0.1×
            kwargs["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]

        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
