"""Schematy API synchronizacji KSeF."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

SubjectType = Literal["Subject1", "Subject2"]


class KsefSyncPeriodRequest(BaseModel):
    date_from: date = Field(description="Początek zakresu")
    date_to: date = Field(description="Koniec zakresu")

    @model_validator(mode="after")
    def validate_order(self) -> "KsefSyncPeriodRequest":
        if self.date_to < self.date_from:
            raise ValueError("date_to nie może być wcześniejsza niż date_from")
        if (self.date_to - self.date_from).days > 90:
            raise ValueError(
                "Jeden żądanie sync nie może przekraczać 90 dni — "
                "użyj krótszych okresów (np. 7 dni)"
            )
        return self


class KsefSyncRequest(BaseModel):
    date_from: date = Field(description="Początek zakresu (data wystawienia faktury, P_1)")
    date_to: date = Field(description="Koniec zakresu (data wystawienia faktury, P_1)")
    subject_type: SubjectType = Field(
        default="Subject2",
        description="Subject1 = sprzedawca (wystawione), Subject2 = nabywca (kosztowe)",
    )

    @model_validator(mode="after")
    def validate_order(self) -> "KsefSyncRequest":
        if self.date_to < self.date_from:
            raise ValueError("date_to nie może być wcześniejsza niż date_from")
        if (self.date_to - self.date_from).days > 90:
            raise ValueError(
                "Jeden żądanie sync nie może przekraczać 90 dni — "
                "użyj krótszych okresów (np. 7 dni)"
            )
        return self


class KsefSyncResponse(BaseModel):
    export_reference_number: str
    date_from: date
    date_to: date
    package_invoice_count: int
    invoices_processed: int
    invoices_failed: int
    lines_processed: int
    is_truncated: bool
    chunks_processed: int = 0
    truncated_periods: int = 0
    errors: list[str] = Field(default_factory=list)


class KsefSyncJobResponse(BaseModel):
    id: UUID
    status: str
    date_from: date
    date_to: date
    progress_message: str | None = None
    error_message: str | None = None
    result: KsefSyncResponse | None = None
    created_at: datetime
    completed_at: datetime | None = None


class KsefSyncJobCreatedResponse(BaseModel):
    job_id: UUID
    status: str = "pending"
