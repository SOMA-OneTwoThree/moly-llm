from app.config import settings
from app.llm.base import StreamingLLMProvider


def create_llm_provider() -> StreamingLLMProvider:
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        from app.llm.anthropic import AnthropicStreamingLLMProvider

        return AnthropicStreamingLLMProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.llm_max_tokens,
        )

    if provider == "groq":
        from app.llm.groq import GroqStreamingLLMProvider

        return GroqStreamingLLMProvider(
            api_key=settings.groq_api_key,
            model=settings.llm_model,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r} (expected 'anthropic' or 'groq')")
