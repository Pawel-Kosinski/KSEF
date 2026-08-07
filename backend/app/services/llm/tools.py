"""Narzędzia Function Calling (Bedrock Converse API + wykonanie lokalne)."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.statistics import StatisticsService
from app.services.llm.types import ToolDefinition

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any], "ToolExecutionContext"], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    tenant_id: UUID
    session: AsyncSession


GET_FINANCIAL_SUMMARY_TOOL = ToolDefinition(
    name="get_financial_summary",
    description=(
        "Pobiera zagregowane przychody (sprzedaż), koszty oraz saldo netto "
        "dla firmy w podanym zakresie dat faktur (issue_date, format YYYY-MM-DD)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "date_from": {
                "type": "string",
                "description": "Data początkowa zakresu (YYYY-MM-DD)",
            },
            "date_to": {
                "type": "string",
                "description": "Data końcowa zakresu (YYYY-MM-DD)",
            },
        },
        "required": ["date_from", "date_to"],
    },
)


def get_bedrock_tool_config() -> dict[str, Any]:
    """Konfiguracja toolConfig dla AWS Bedrock Converse API."""
    return {
        "tools": [GET_FINANCIAL_SUMMARY_TOOL.to_bedrock_tool_spec()],
    }


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

    def get_bedrock_tool_config(self) -> dict[str, Any]:
        return {
            "tools": [tool.definition.to_bedrock_tool_spec() for tool in self._tools.values()],
        }

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
            return json.dumps({"error": str(exc), "tool": name}, ensure_ascii=False)


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Nieprawidłowa data w polu '{field_name}': {value}") from exc


def _summary_to_dict(summary: Any) -> dict[str, Any]:
    return {
        "total_net": str(summary.total_net),
        "total_vat": str(summary.total_vat),
        "total_gross": str(summary.total_gross),
        "date_from": summary.date_from.isoformat() if summary.date_from else None,
        "date_to": summary.date_to.isoformat() if summary.date_to else None,
        "role": summary.role,
    }


async def get_financial_summary(
    arguments: dict[str, Any],
    context: ToolExecutionContext,
) -> dict[str, Any]:
    """
    Wykonuje zapytanie o podsumowanie finansowe dla tenanta (RLS przez sesję).
    Bezwzględnie wymaga tenant_id z warstwy autoryzacji (ToolExecutionContext).
    """
    date_from = _parse_iso_date(str(arguments["date_from"]), "date_from")
    date_to = _parse_iso_date(str(arguments["date_to"]), "date_to")
    if date_from > date_to:
        raise ValueError("date_from nie może być późniejsza niż date_to")

    service = StatisticsService(context.session, context.tenant_id)
    costs = await service.get_summary(role="cost", date_from=date_from, date_to=date_to)
    revenue = await service.get_summary(role="sales", date_from=date_from, date_to=date_to)

    costs_net = costs.total_net
    revenue_net = revenue.total_net

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "currency": "PLN",
        "costs": _summary_to_dict(costs),
        "revenue": _summary_to_dict(revenue),
        "balance": str(revenue_net - costs_net),
        "net_result": str(revenue_net - costs_net),
    }


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GET_FINANCIAL_SUMMARY_TOOL, get_financial_summary)
    return registry


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return build_default_tool_registry()
