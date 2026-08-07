"""Abstrakcyjny adapter LLM – wzorzec Strategy / Adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.services.llm.types import LLMMessage, LLMStreamEvent, ToolDefinition


class BaseLLMService(ABC):
    """Kontrakt dla dostawców modeli językowych (Claude, Bedrock, …)."""

    @abstractmethod
    async def generate_response(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
    ) -> AsyncIterator[LLMStreamEvent]:
        """
        Generuje odpowiedź modelu ze strumieniowaniem.

        Zdarzenia:
        - text_delta: fragment tekstu asystenta
        - tool_call: kompletne żądanie użycia narzędzia
        - message_complete: koniec odpowiedzi (z pełną wiadomością asystenta)
        - error: błąd dostawcy
        """
        raise NotImplementedError
        yield  # pragma: no cover
