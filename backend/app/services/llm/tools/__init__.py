"""Inicjalizacja rejestru narzędzi Virtual CFO."""

from functools import lru_cache

from app.services.llm.tools.financial_summary import (
    GET_FINANCIAL_SUMMARY_TOOL,
    handle_get_financial_summary,
)
from app.services.llm.tools.registry import ToolRegistry


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GET_FINANCIAL_SUMMARY_TOOL, handle_get_financial_summary)
    return registry


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return build_default_tool_registry()
