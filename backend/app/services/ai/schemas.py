"""Schematy Pydantic dla modułu kategoryzacji AI – dynamiczne kategorie per tenant."""

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, create_model, field_validator

# Domyślne kategorie seedowane dla nowych tenantów (plan projektu MVP)
DEFAULT_TENANT_CATEGORIES: tuple[str, ...] = (
    "Materiały i Surowce",
    "Opakowania",
    "Paliwa i Transport",
    "Koszty Biurowe i IT",
    "Usługi Zewnętrzne",
    "Inne Koszty Operacyjne",
)


class CategoryClassificationBase(BaseModel):
    """Wspólna struktura odpowiedzi modelu – niezależna od listy kategorii."""

    kategoria_podrzedna: str = Field(
        description="Bardziej szczegółowy opis kategorii stworzony w języku polskim (maksymalnie 3 słowa)."
    )
    pewnosc_klasyfikacji: int = Field(
        ge=0,
        le=100,
        description="Wartość od 0 do 100 określająca stopień zaufania modelu do własnej klasyfikacji.",
    )

    @field_validator("kategoria_podrzedna", mode="before")
    @classmethod
    def trim_to_three_words(cls, value: str) -> str:
        words = str(value).strip().split()
        if not words:
            raise ValueError("kategoria_podrzedna nie może być pusta")
        return " ".join(words[:3])


def validate_allowed_categories(allowed_categories: list[str]) -> list[str]:
    if not allowed_categories:
        raise ValueError("allowed_categories nie może być pusta")
    cleaned = [c.strip() for c in allowed_categories if c and c.strip()]
    if not cleaned:
        raise ValueError("allowed_categories nie może być pusta")
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("allowed_categories zawiera duplikaty")
    return cleaned


def build_category_schema(
    allowed_categories: list[str],
) -> type[BaseModel]:
    """
    Dynamiczny schemat Structured Output dla Ollama.
    kategoria_glowna = Literal z wartościami tenant-specific.
    """
    categories = validate_allowed_categories(allowed_categories)
    category_literal = Literal[tuple(categories)]  # type: ignore[valid-type]

    return create_model(
        "DynamicAICategorySchema",
        __base__=CategoryClassificationBase,
        kategoria_glowna=(
            category_literal,
            Field(description="Główna gałąź z drzewa kosztowego tenanta."),
        ),
    )


def build_category_json_schema(allowed_categories: list[str]) -> dict[str, Any]:
    """JSON Schema przekazywany do parametru format w kliencie Ollama."""
    schema_cls = build_category_schema(allowed_categories)
    return schema_cls.model_json_schema()


def get_category_literal_values(schema_cls: type[BaseModel]) -> tuple[str, ...]:
    """Wyciąga dozwolone wartości kategoria_glowna ze schematu dynamicznego."""
    field_info = schema_cls.model_fields["kategoria_glowna"]
    return get_args(field_info.annotation)
