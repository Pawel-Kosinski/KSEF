"""Schematy API ustawień tenanta."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KsefSettingsStatus(BaseModel):
    is_configured: bool


class KsefTokenUpdate(BaseModel):
    ksef_token: str = Field(min_length=1, max_length=4096)


class TenantCategoryItem(BaseModel):
    id: UUID
    name: str
    sort_order: int
    invoice_usage_count: int = Field(
        description="Liczba powiązań z fakturami, liniami lub regułami NIP",
    )


class TenantCategoryListResponse(BaseModel):
    categories: list[TenantCategoryItem]


class TenantCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class TenantCategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ContractorRuleItem(BaseModel):
    id: UUID
    contractor_nip: str
    contractor_name: str | None = None
    category_main: str
    category_sub: str
    line_usage_count: int = 0
    updated_at: datetime | None = None


class ContractorRuleListResponse(BaseModel):
    rules: list[ContractorRuleItem]


class TeamMemberItem(BaseModel):
    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime


class TeamResponse(BaseModel):
    invite_token: str
    members: list[TeamMemberItem]


class ContractorRuleCreate(BaseModel):
    contractor_nip: str = Field(min_length=10, max_length=10)
    category_main: str = Field(min_length=1, max_length=128)
    category_sub: str | None = Field(default="Inne", max_length=128)
    contractor_name: str | None = Field(default=None, max_length=255)
