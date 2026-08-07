"""Testy rejestru narzędzi LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.llm.tools import build_default_tool_registry
from app.services.llm.tools.context import ToolExecutionContext
from app.services.llm.tools.registry import ToolRegistry
from app.services.llm.types import ToolDefinition


@pytest.mark.asyncio
async def test_default_registry_contains_financial_summary():
    registry = build_default_tool_registry()
    names = [tool.name for tool in registry.get_definitions()]
    assert "get_financial_summary" in names


@pytest.mark.asyncio
async def test_registry_executes_registered_handler():
    registry = ToolRegistry()

    async def echo_handler(arguments: dict, context: ToolExecutionContext) -> dict:
        return {"tenant_id": str(context.tenant_id), "echo": arguments["value"]}

    registry.register(
        ToolDefinition(
            name="echo_tool",
            description="Echo test",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        ),
        echo_handler,
    )

    tenant_id = uuid4()
    result = await registry.execute(
        "echo_tool",
        {"value": "test"},
        ToolExecutionContext(tenant_id=tenant_id, session=AsyncMock()),
    )

    assert '"echo": "test"' in result
    assert str(tenant_id) in result
