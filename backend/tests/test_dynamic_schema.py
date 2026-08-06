"""Testy dynamicznego schematu kategoryzacji AI."""

import pytest
from pydantic import ValidationError

from app.services.ai.categorizer import build_system_prompt
from app.services.ai.schemas import (
    DEFAULT_TENANT_CATEGORIES,
    build_category_schema,
    validate_allowed_categories,
)


def test_build_dynamic_schema_accepts_valid_category():
    schema_cls = build_category_schema(["Opakowania", "Paliwa i Transport"])
    obj = schema_cls(
        kategoria_glowna="Opakowania",
        kategoria_podrzedna="karton fasonowy",
        pewnosc_klasyfikacji=88,
    )
    assert obj.kategoria_glowna == "Opakowania"


def test_build_dynamic_schema_rejects_unknown_category():
    schema_cls = build_category_schema(["Opakowania"])
    with pytest.raises(ValidationError):
        schema_cls(
            kategoria_glowna="Paliwa i Transport",
            kategoria_podrzedna="diesel",
            pewnosc_klasyfikacji=50,
        )


def test_system_prompt_injects_categories():
    categories = ["Kategoria A", "Kategoria B"]
    prompt = build_system_prompt(categories)
    assert '"Kategoria A"' in prompt
    assert '"Kategoria B"' in prompt
    assert "Materiały i Surowce" not in prompt


def test_validate_rejects_empty_list():
    with pytest.raises(ValueError, match="nie może być pusta"):
        validate_allowed_categories([])


def test_default_categories_count():
    assert len(DEFAULT_TENANT_CATEGORIES) == 6
