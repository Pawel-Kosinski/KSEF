"""Testy pętli agenta Virtual CFO Chat."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.llm.agent import ChatAgentService
from app.services.llm.base import BaseLLMService
from app.services.llm.tools import build_default_tool_registry
from app.services.llm.tools.context import ToolExecutionContext
from app.services.llm.types import (
    LLMMessage,
    LLMStreamEvent,
    TextContentBlock,
    ToolCall,
    ToolDefinition,
    ToolUseContentBlock,
)


class ScriptedLLMService(BaseLLMService):
    def __init__(self, scripts: list[list[LLMStreamEvent]]) -> None:
        self._scripts = scripts
        self._call_index = 0

    async def generate_response(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition],
    ) -> AsyncIterator[LLMStreamEvent]:
        if self._call_index >= len(self._scripts):
            raise RuntimeError("Brak skryptu odpowiedzi LLM")
        events = self._scripts[self._call_index]
        self._call_index += 1
        for event in events:
            yield event


async def _collect_events(
    agent: ChatAgentService,
    history: list[dict[str, str]],
    context: ToolExecutionContext,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    async for event in agent.stream_chat(history, context):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_agent_executes_tool_then_streams_final_answer():
    tool_call = ToolCall(
        id="toolu_01",
        name="get_financial_summary",
        arguments={"date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    llm = ScriptedLLMService(
        [
            [
                LLMStreamEvent(type="tool_call", tool_call=tool_call),
                LLMStreamEvent(
                    type="message_complete",
                    assistant_message=LLMMessage(
                        role="assistant",
                        content=[
                            ToolUseContentBlock(
                                id=tool_call.id,
                                name=tool_call.name,
                                input=tool_call.arguments,
                            )
                        ],
                    ),
                ),
            ],
            [
                LLMStreamEvent(type="text_delta", text="Przychody w styczniu "),
                LLMStreamEvent(type="text_delta", text="wyniosły 10 000 PLN."),
                LLMStreamEvent(
                    type="message_complete",
                    assistant_message=LLMMessage(
                        role="assistant",
                        content=[TextContentBlock(text="Przychody w styczniu wyniosły 10 000 PLN.")],
                    ),
                ),
            ],
        ]
    )

    registry = build_default_tool_registry()
    original = registry._tools["get_financial_summary"]
    registry._tools["get_financial_summary"] = type(original)(
        definition=original.definition,
        handler=AsyncMock(
            return_value={
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "currency": "PLN",
                "costs": {"total_net": "1000.00"},
                "revenue": {"total_net": "10000.00"},
                "net_result": "9000.00",
            }
        ),
    )

    agent = ChatAgentService(llm=llm, tools=registry)
    context = ToolExecutionContext(tenant_id=uuid4(), session=AsyncMock())
    events = await _collect_events(
        agent,
        [{"role": "user", "content": "Podsumuj styczeń 2026"}],
        context,
    )

    types = [event["type"] for event in events]
    assert "tool_start" in types
    assert "tool_result" in types
    assert types.count("text") >= 1
    assert events[-1]["type"] == "done"
    assert llm._call_index == 2


@pytest.mark.asyncio
async def test_agent_rejects_history_not_ending_with_user():
    agent = ChatAgentService(
        llm=ScriptedLLMService([]),
        tools=build_default_tool_registry(),
    )
    context = ToolExecutionContext(tenant_id=uuid4(), session=AsyncMock())

    events = await _collect_events(
        agent,
        [
            {"role": "user", "content": "Pytanie"},
            {"role": "assistant", "content": "Odpowiedź"},
        ],
        context,
    )

    assert events[0]["type"] == "error"


@pytest.mark.asyncio
async def test_agent_returns_done_without_tools_for_direct_answer():
    llm = ScriptedLLMService(
        [
            [
                LLMStreamEvent(type="text_delta", text="Cześć!"),
                LLMStreamEvent(
                    type="message_complete",
                    assistant_message=LLMMessage(role="assistant", content="Cześć!"),
                ),
            ]
        ]
    )
    agent = ChatAgentService(llm=llm, tools=build_default_tool_registry())
    context = ToolExecutionContext(tenant_id=uuid4(), session=AsyncMock())

    events = await _collect_events(
        agent,
        [{"role": "user", "content": "Hej"}],
        context,
    )

    assert events[0] == {"type": "text", "content": "Cześć!"}
    assert events[-1] == {"type": "done"}
