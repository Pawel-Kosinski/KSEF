"""Kontekst wykonania narzędzi (tenant + sesja RLS)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    tenant_id: UUID
    session: AsyncSession
