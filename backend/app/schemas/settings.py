"""Schematy API ustawień tenanta."""

from pydantic import BaseModel, Field


class KsefSettingsStatus(BaseModel):
    is_configured: bool


class KsefTokenUpdate(BaseModel):
    ksef_token: str = Field(min_length=1, max_length=4096)
