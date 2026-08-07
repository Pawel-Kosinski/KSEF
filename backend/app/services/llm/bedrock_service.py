"""Adapter Amazon Bedrock (Converse API) – Claude 3.5 Haiku."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import boto3
from botocore.config import Config

from app.config import Settings, get_settings
from app.services.llm.base import BaseLLMService
from app.services.llm.types import (
    LLMMessage,
    LLMStreamEvent,
    TextContentBlock,
    ToolCall,
    ToolDefinition,
    ToolResultContentBlock,
    ToolUseContentBlock,
)

logger = logging.getLogger(__name__)

VIRTUAL_CFO_SYSTEM_PROMPT = """Jesteś Wirtualnym CFO – asystentem finansowym dla polskich MŚP.
Analizujesz dane z faktur KSeF (koszty i przychody) i odpowiadasz zwięźle po polsku.
Gdy potrzebujesz liczb z systemu, wywołuj dostępne narzędzia zamiast zgadywać.
Podawaj kwoty w PLN z dwoma miejscami po przecinku."""


class BedrockLLMService(BaseLLMService):
    """Implementacja BaseLLMService przez boto3 bedrock-runtime converse_stream."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        system_prompt: str = VIRTUAL_CFO_SYSTEM_PROMPT,
    ) -> None:
        self._settings = settings or get_settings()
        self._model_id = self._settings.bedrock_model_id
        self._max_tokens = self._settings.bedrock_max_tokens
        self._system_prompt = system_prompt
        self._client = self._create_client()

    def _create_client(self):
        client_kwargs: dict[str, Any] = {
            "region_name": self._settings.aws_default_region,
            "config": Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=300,
            ),
        }
        access_key = self._settings.aws_access_key_id.strip()
        secret_key = self._settings.aws_secret_access_key.strip()
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        return boto3.client("bedrock-runtime", **client_kwargs)

    @staticmethod
    def _serialize_content(content: str | list[Any]) -> list[dict[str, Any]]:
        if isinstance(content, str):
            return [{"text": content}]

        blocks: list[dict[str, Any]] = []
        for block in content:
            if isinstance(block, TextContentBlock):
                blocks.append({"text": block.text})
            elif isinstance(block, ToolUseContentBlock):
                blocks.append(
                    {
                        "toolUse": {
                            "toolUseId": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    }
                )
            elif isinstance(block, ToolResultContentBlock):
                blocks.append(
                    {
                        "toolResult": {
                            "toolUseId": block.tool_use_id,
                            "content": [{"text": block.content}],
                        }
                    }
                )
        return blocks

    def _to_bedrock_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        bedrock_messages: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                continue
            bedrock_messages.append(
                {
                    "role": message.role,
                    "content": self._serialize_content(message.content),
                }
            )
        return bedrock_messages

    @staticmethod
    def _build_tool_config(tools: list[ToolDefinition]) -> dict[str, Any] | None:
        if not tools:
            return None
        return {"tools": [tool.to_bedrock_tool_spec() for tool in tools]}

    def _converse_stream_sync(
        self,
        messages: list[dict[str, Any]],
        tool_config: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "modelId": self._model_id,
            "messages": messages,
            "system": [{"text": self._system_prompt}],
            "inferenceConfig": {"maxTokens": self._max_tokens, "temperature": 0.2},
        }
        if tool_config:
            params["toolConfig"] = tool_config

        response = self._client.converse_stream(**params)
        return list(response.get("stream", []))

    async def stream_conversation(
        self,
        messages: list[dict[str, Any]],
        tool_config: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Strumieniuje surowe zdarzenia z converse_stream (w wątku roboczym)."""
        events = await asyncio.to_thread(self._converse_stream_sync, messages, tool_config)
        for event in events:
            yield event

    @staticmethod
    def _parse_tool_input(raw_input: str) -> dict[str, Any]:
        if not raw_input:
            return {}
        try:
            parsed = json.loads(raw_input)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _bedrock_blocks_to_assistant_message(
        text_parts: list[str],
        tool_uses: list[ToolUseContentBlock],
    ) -> LLMMessage:
        blocks: list[TextContentBlock | ToolUseContentBlock] = []
        text = "".join(text_parts).strip()
        if text:
            blocks.append(TextContentBlock(text=text))
        blocks.extend(tool_uses)
        if len(blocks) == 1 and isinstance(blocks[0], TextContentBlock):
            return LLMMessage(role="assistant", content=blocks[0].text)
        return LLMMessage(role="assistant", content=blocks)

    async def generate_response(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
    ) -> AsyncIterator[LLMStreamEvent]:
        bedrock_messages = self._to_bedrock_messages(messages)
        tool_config = self._build_tool_config(tools)

        pending_tools: dict[int, dict[str, Any]] = {}
        text_parts: list[str] = []
        completed_tool_uses: list[ToolUseContentBlock] = []

        try:
            async for event in self.stream_conversation(bedrock_messages, tool_config):
                if "contentBlockStart" in event:
                    start = event["contentBlockStart"].get("start", {})
                    if "toolUse" in start:
                        index = event["contentBlockStart"]["contentBlockIndex"]
                        tool_use = start["toolUse"]
                        pending_tools[index] = {
                            "id": tool_use["toolUseId"],
                            "name": tool_use["name"],
                            "input_json": "",
                        }
                elif "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        text_parts.append(delta["text"])
                        yield LLMStreamEvent(type="text_delta", text=delta["text"])
                    elif "toolUse" in delta:
                        index = event["contentBlockDelta"]["contentBlockIndex"]
                        tool_state = pending_tools.get(index)
                        if tool_state is not None:
                            tool_state["input_json"] += delta["toolUse"].get("input", "")
                elif "contentBlockStop" in event:
                    index = event["contentBlockStop"]["contentBlockIndex"]
                    state = pending_tools.pop(index, None)
                    if state is None:
                        continue
                    arguments = self._parse_tool_input(state.get("input_json", ""))
                    tool_use_block = ToolUseContentBlock(
                        id=state["id"],
                        name=state["name"],
                        input=arguments,
                    )
                    completed_tool_uses.append(tool_use_block)
                    yield LLMStreamEvent(
                        type="tool_call",
                        tool_call=ToolCall(
                            id=state["id"],
                            name=state["name"],
                            arguments=arguments,
                        ),
                    )
        except Exception as exc:
            logger.exception("Błąd strumienia Bedrock converse_stream")
            yield LLMStreamEvent(type="error", error=str(exc))
            return

        yield LLMStreamEvent(
            type="message_complete",
            assistant_message=self._bedrock_blocks_to_assistant_message(
                text_parts,
                completed_tool_uses,
            ),
        )
