"""Schematy API autoryzacji."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(min_length=2, max_length=255)
    nip: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    tenant_id: UUID
    is_active: bool
    company_name: str | None = None
    nip: str | None = None
