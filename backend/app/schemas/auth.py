"""Schematy API autoryzacji."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str | None = Field(default=None, min_length=2, max_length=255)
    nip: str | None = Field(default=None, min_length=10, max_length=10, pattern=r"^\d{10}$")
    industry: str | None = Field(
        default=None,
        min_length=3,
        max_length=512,
        description="Branża / opis działalności firmy",
    )
    invite_token: str | None = Field(
        default=None,
        min_length=36,
        max_length=36,
        description="Kod zaproszenia do istniejącej firmy",
    )

    @model_validator(mode="after")
    def validate_registration_mode(self) -> "RegisterRequest":
        token = (self.invite_token or "").strip()
        if token:
            if self.company_name or self.nip or self.industry:
                raise ValueError(
                    "Przy dołączaniu do zespołu podaj tylko e-mail, hasło i kod zaproszenia"
                )
            object.__setattr__(self, "invite_token", token)
            return self

        if not self.company_name or not self.nip or not self.industry:
            raise ValueError(
                "Rejestracja nowej firmy wymaga nazwy, NIP, branży oraz e-maila i hasła"
            )
        object.__setattr__(self, "company_name", self.company_name.strip())
        object.__setattr__(self, "industry", self.industry.strip())
        return self

    @property
    def is_invite_registration(self) -> bool:
        return bool(self.invite_token)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    tenant_id: UUID
    is_active: bool
    role: str
    company_name: str | None = None
    nip: str | None = None
    industry: str | None = None
