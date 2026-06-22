from app.config import settings
from app.llm.base import StreamingLLMProvider
from app.llm.groq import GroqStreamingLLMProvider


def create_llm_provider() -> StreamingLLMProvider:
    return GroqStreamingLLMProvider(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
    )
