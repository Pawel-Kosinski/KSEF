"""Pętla agenta Virtual CFO (tool use + strumieniowanie odpowiedzi)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.services.llm.base import BaseLLMService
from app.services.llm.tools import ToolExecutionContext, ToolRegistry
from app.services.llm.types import (
    LLMMessage,
    ToolCall,
    ToolResultContentBlock,
    ToolUseContentBlock,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 8


class ChatAgentService:
    """Orkiestruje konwersację z modelem i lokalnym wykonaniem narzędzi."""

    def __init__(
        self,
        llm: BaseLLMService,
        tools: ToolRegistry,
        *,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._max_iterations = max_iterations

    @staticmethod
    def _history_to_llm_messages(history: list[dict[str, str]]) -> list[LLMMessage]:
        messages: list[LLMMessage] = []
        for item in history:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role not in ("user", "assistant") or not content:
                continue
            messages.append(LLMMessage(role=role, content=content))
        return messages

    async def stream_chat(
        self,
        history: list[dict[str, str]],
        context: ToolExecutionContext,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Uruchamia pętlę agenta i zwraca zdarzenia SSE-ready:
        - {"type": "text", "content": "..."}
        - {"type": "tool_start", "tool_name": "...", "tool_call_id": "..."}
        - {"type": "tool_result", "tool_name": "...", "content": "..."}
        - {"type": "done"}
        - {"type": "error", "content": "..."}
        """
        messages = self._history_to_llm_messages(history)
        if not messages or messages[-1].role != "user":
            yield {"type": "error", "content": "Ostatnia wiadomość w historii musi być od użytkownika"}
            return

        tool_definitions = self._tools.get_definitions()

        for iteration in range(self._max_iterations):
            tool_calls: list[ToolCall] = []
            assistant_message: LLMMessage | None = None

            async for event in self._llm.generate_response(messages, tool_definitions):
                if event.type == "text_delta" and event.text:
                    yield {"type": "text", "content": event.text}
                elif event.type == "tool_call" and event.tool_call:
                    tool_calls.append(event.tool_call)
                elif event.type == "error":
                    yield {"type": "error", "content": event.error or "Błąd modelu LLM"}
                    return
                elif event.type == "message_complete" and event.assistant_message:
                    assistant_message = event.assistant_message

            if assistant_message is None:
                yield {"type": "error", "content": "Model nie zwrócił odpowiedzi"}
                return

            if not tool_calls:
                if isinstance(assistant_message.content, list):
                    for block in assistant_message.content:
                        if isinstance(block, ToolUseContentBlock):
                            tool_calls.append(
                                ToolCall(
                                    id=block.id,
                                    name=block.name,
                                    arguments=block.input,
                                )
                            )

            if not tool_calls:
                yield {"type": "done"}
                return

            messages.append(assistant_message)
            tool_result_blocks: list[ToolResultContentBlock] = []

            for tool_call in tool_calls:
                yield {
                    "type": "tool_start",
                    "tool_name": tool_call.name,
                    "tool_call_id": tool_call.id,
                }

                if not self._tools.has_tool(tool_call.name):
                    result_content = (
                        f'{{"error": "Nieznane narzędzie: {tool_call.name}"}}'
                    )
                else:
                    result_content = await self._tools.execute(
                        tool_call.name,
                        tool_call.arguments,
                        context,
                    )

                yield {
                    "type": "tool_result",
                    "tool_name": tool_call.name,
                    "tool_call_id": tool_call.id,
                    "content": result_content,
                }

                tool_result_blocks.append(
                    ToolResultContentBlock(
                        tool_use_id=tool_call.id,
                        content=result_content,
                    )
                )

            messages.append(LLMMessage(role="user", content=tool_result_blocks))

            logger.debug("Agent loop iteration %s – wykonano %s narzędzi", iteration + 1, len(tool_calls))

        yield {
            "type": "error",
            "content": f"Przekroczono limit iteracji agenta ({self._max_iterations})",
        }
