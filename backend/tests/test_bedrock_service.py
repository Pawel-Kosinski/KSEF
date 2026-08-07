"""Testy adaptera Amazon Bedrock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.llm.bedrock_service import BedrockLLMService
from app.services.llm.types import LLMMessage, ToolDefinition


@pytest.fixture
def bedrock_service():
    with patch("app.services.llm.bedrock_service.boto3.client") as mock_client_ctor:
        mock_client = MagicMock()
        mock_client_ctor.return_value = mock_client
        service = BedrockLLMService()
        service._client = mock_client
        yield service, mock_client


@pytest.mark.asyncio
async def test_stream_conversation_yields_text_delta(bedrock_service):
    service, mock_client = bedrock_service
    mock_client.converse_stream.return_value = {
        "stream": [
            {"contentBlockDelta": {"contentBlockIndex": 0, "delta": {"text": "Witaj"}}},
            {"contentBlockStop": {"contentBlockIndex": 0}},
            {"messageStop": {"stopReason": "end_turn"}},
        ]
    }

    events = []
    async for event in service.generate_response(
        [LLMMessage(role="user", content="Cześć")],
        [],
    ):
        events.append(event)

    assert any(event.type == "text_delta" and event.text == "Witaj" for event in events)
    assert events[-1].type == "message_complete"
    mock_client.converse_stream.assert_called_once()


@pytest.mark.asyncio
async def test_stream_conversation_parses_tool_use(bedrock_service):
    service, mock_client = bedrock_service
    mock_client.converse_stream.return_value = {
        "stream": [
            {
                "contentBlockStart": {
                    "contentBlockIndex": 0,
                    "start": {
                        "toolUse": {
                            "toolUseId": "toolu_123",
                            "name": "get_financial_summary",
                        }
                    },
                }
            },
            {
                "contentBlockDelta": {
                    "contentBlockIndex": 0,
                    "delta": {
                        "toolUse": {
                            "input": '{"date_from": "2026-01-01", "date_to": "2026-01-31"}'
                        }
                    },
                }
            },
            {"contentBlockStop": {"contentBlockIndex": 0}},
            {"messageStop": {"stopReason": "tool_use"}},
        ]
    }

    events = []
    async for event in service.generate_response(
        [LLMMessage(role="user", content="Podsumuj styczeń")],
        [
            ToolDefinition(
                name="get_financial_summary",
                description="test",
                input_schema={"type": "object", "properties": {}},
            )
        ],
    ):
        events.append(event)

    tool_events = [event for event in events if event.type == "tool_call"]
    assert len(tool_events) == 1
    assert tool_events[0].tool_call is not None
    assert tool_events[0].tool_call.name == "get_financial_summary"
    assert tool_events[0].tool_call.arguments["date_from"] == "2026-01-01"
