"""Adapter Claude 3.5 Sonnet (Anthropic API) ze strumieniowaniem i tool use."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic, NotGiven
from anthropic.types import ContentBlock as AnthropicContentBlock

from app.config import Settings, get_settings
from app.services.llm.base import BaseLLMService
from app.services.llm.types import (
    LLMMessage,
    LLMStreamEvent,
    TextContentBlock,
    ToolCall,
    ToolDefinition,
    ToolUseContentBlock,
)

logger = logging.getLogger(__name__)

VIRTUAL_CFO_SYSTEM_PROMPT = """Jesteś Wirtualnym CFO – asystentem finansowym dla polskich MŚP.
Analizujesz dane z faktur KSeF (koszty i przychody) i odpowiadasz zwięźle po polsku.
Gdy potrzebujesz liczb z systemu, wywołuj dostępne narzędzia zamiast zgadywać.
Podawaj kwoty w PLN z dwoma miejscami po przecinku."""


class ClaudeLLMService(BaseLLMService):
    """Implementacja BaseLLMService dla Anthropic Claude."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        system_prompt: str = VIRTUAL_CFO_SYSTEM_PROMPT,
    ) -> None:
        self._settings = settings or get_settings()
        if not self._settings.anthropic_api_key.strip():
            raise ValueError("ANTHROPIC_API_KEY jest wymagany dla ClaudeLLMService")
        self._client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        self._model = self._settings.anthropic_model
        self._max_tokens = self._settings.anthropic_max_tokens
        self._system_prompt = system_prompt

    def _split_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        api_messages: list[dict[str, Any]] = []

        for message in messages:
            if message.role == "system":
                if isinstance(message.content, str):
                    system_parts.append(message.content)
                continue

            api_messages.append(
                {
                    "role": message.role,
                    "content": self._serialize_content(message.content),
                }
            )

        system = self._system_prompt
        if system_parts:
            system = f"{system}\n\n" + "\n".join(system_parts)
        return system, api_messages

    @staticmethod
    def _serialize_content(content: str | list[Any]) -> str | list[dict[str, Any]]:
        if isinstance(content, str):
            return content

        blocks: list[dict[str, Any]] = []
        for block in content:
            if isinstance(block, TextContentBlock):
                blocks.append({"type": "text", "text": block.text})
            elif isinstance(block, ToolUseContentBlock):
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
            else:
                blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                    }
                )
        return blocks

    @staticmethod
    def _anthropic_block_to_domain(
        block: AnthropicContentBlock,
    ) -> TextContentBlock | ToolUseContentBlock:
        if block.type == "text":
            return TextContentBlock(text=block.text)
        return ToolUseContentBlock(
            id=block.id,
            name=block.name,
            input=dict(block.input),
        )

    @staticmethod
    def _build_assistant_message(blocks: list[TextContentBlock | ToolUseContentBlock]) -> LLMMessage:
        return LLMMessage(role="assistant", content=blocks)

    async def generate_response(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
    ) -> AsyncIterator[LLMStreamEvent]:
        system, api_messages = self._split_messages(messages)
        tool_specs = [tool.to_anthropic_tool() for tool in tools] if tools else None

        pending_tools: dict[int, dict[str, Any]] = {}

        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=api_messages,
                tools=tool_specs if tool_specs else NotGiven(),
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "tool_use":
                            pending_tools[event.index] = {
                                "id": block.id,
                                "name": block.name,
                                "input_json": "",
                            }
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            yield LLMStreamEvent(type="text_delta", text=delta.text)
                        elif delta.type == "input_json_delta":
                            tool_state = pending_tools.get(event.index)
                            if tool_state is not None:
                                tool_state["input_json"] += delta.partial_json
                    elif event.type == "content_block_stop":
                        state = pending_tools.pop(event.index, None)
                        if state is None:
                            continue
                        raw_input = state.get("input_json", "")
                        try:
                            arguments = json.loads(raw_input) if raw_input else {}
                        except json.JSONDecodeError:
                            arguments = {}
                        yield LLMStreamEvent(
                            type="tool_call",
                            tool_call=ToolCall(
                                id=state["id"],
                                name=state["name"],
                                arguments=arguments,
                            ),
                        )

                final = await stream.get_final_message()
        except Exception as exc:
            logger.exception("Błąd strumienia Claude")
            yield LLMStreamEvent(type="error", error=str(exc))
            return

        content_blocks: list[TextContentBlock | ToolUseContentBlock] = []
        for block in final.content:
            content_blocks.append(self._anthropic_block_to_domain(block))

        yield LLMStreamEvent(
            type="message_complete",
            assistant_message=self._build_assistant_message(content_blocks),
        )
