"""Narzędzie: podsumowanie finansowe (przychody i koszty) dla tenanta."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.analytics.statistics import StatisticsService
from app.services.llm.tools.context import ToolExecutionContext
from app.services.llm.types import ToolDefinition

GET_FINANCIAL_SUMMARY_TOOL = ToolDefinition(
    name="get_financial_summary",
    description=(
        "Pobiera zagregowane przychody (sprzedaż) i koszty netto/VAT/brutto "
        "dla firmy w podanym zakresie dat faktur (issue_date, format YYYY-MM-DD)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "date_from": {
                "type": "string",
                "description": "Data początkowa zakresu (YYYY-MM-DD)",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
            "date_to": {
                "type": "string",
                "description": "Data końcowa zakresu (YYYY-MM-DD)",
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
            },
        },
        "required": ["date_from", "date_to"],
        "additionalProperties": False,
    },
)


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


async def handle_get_financial_summary(
    arguments: dict[str, Any],
    context: ToolExecutionContext,
) -> dict[str, Any]:
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
        "net_result": str(revenue_net - costs_net),
    }
