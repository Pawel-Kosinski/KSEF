"""Fabryka usług LLM."""

from functools import lru_cache

from app.config import get_settings
from app.services.llm.base import BaseLLMService
from app.services.llm.bedrock_service import BedrockLLMService
from app.services.llm.claude import ClaudeLLMService


@lru_cache
def get_llm_service() -> BaseLLMService:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "bedrock":
        return BedrockLLMService(settings)
    if provider == "claude":
        return ClaudeLLMService(settings)
    raise ValueError(f"Nieobsługiwany dostawca LLM: {settings.llm_provider}")
