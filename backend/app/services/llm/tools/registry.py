"""Rejestr narzędzi Function Calling dla Virtual CFO Chat."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.services.llm.tools.context import ToolExecutionContext
from app.services.llm.types import ToolDefinition

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any], ToolExecutionContext], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    definition: ToolDefinition
    handler: ToolHandler


class ToolRegistry:
    """Centralny rejestr narzędzi dostępnych dla agenta."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Narzędzie '{definition.name}' jest już zarejestrowane")
        self._tools[definition.name] = RegisteredTool(definition=definition, handler=handler)

    def get_definitions(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ToolExecutionContext,
    ) -> str:
        registered = self._tools.get(name)
        if registered is None:
            raise KeyError(f"Nieznane narzędzie: {name}")

        try:
            result = await registered.handler(arguments, context)
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.exception("Błąd wykonania narzędzia %s", name)
            return json.dumps(
                {"error": str(exc), "tool": name},
                ensure_ascii=False,
            )
