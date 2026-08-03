"""Testy izolacji danych wejściowych – bez wywołania Ollama."""

import pytest

from app.services.ai.categorizer import _assert_product_name_isolation, build_system_prompt
from app.services.ai.exceptions import AIInputIsolationError
from app.services.ai.schemas import build_category_schema


def test_dynamic_schema_validates_subcategory():
    schema_cls = build_category_schema(["Opakowania", "Inne Koszty Operacyjne"])
    obj = schema_cls(
        kategoria_glowna="Opakowania",
        kategoria_podrzedna="karton fasonowy",
        pewnosc_klasyfikacji=90,
    )
    assert obj.kategoria_podrzedna == "karton fasonowy"


def test_dynamic_schema_rejects_empty_subcategory():
    schema_cls = build_category_schema(["Opakowania"])
    with pytest.raises(ValueError, match="nie może być pusta"):
        schema_cls(
            kategoria_glowna="Opakowania",
            kategoria_podrzedna="   ",
            pewnosc_klasyfikacji=50,
        )


def test_dynamic_schema_truncates_subcategory():
    schema_cls = build_category_schema(["Opakowania"])
    obj = schema_cls(
        kategoria_glowna="Opakowania",
        kategoria_podrzedna="za dużo słów tutaj",
        pewnosc_klasyfikacji=50,
    )
    assert obj.kategoria_podrzedna == "za dużo słów"


def test_isolation_rejects_nip():
    with pytest.raises(AIInputIsolationError, match="NIP"):
        _assert_product_name_isolation("Faktura za usługi 1234567890")


def test_isolation_rejects_amount():
    with pytest.raises(AIInputIsolationError, match="kwot"):
        _assert_product_name_isolation("Usługa konsultingowa 1500,00 PLN")


def test_isolation_accepts_product_name():
    assert _assert_product_name_isolation("  ON BP  ") == "ON BP"
    assert _assert_product_name_isolation("Elektrody spawalnicze 3.2mm") == "Elektrody spawalnicze 3.2mm"


def test_build_system_prompt_lists_only_allowed():
    prompt = build_system_prompt(["Koszt A", "Koszt B"])
    assert "Koszt A" in prompt
    assert "Paliwa i Transport" not in prompt
