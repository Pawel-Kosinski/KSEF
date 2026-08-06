"""Testy generatora kategorii – parsowanie JSON bez Ollama."""

import pytest

from app.services.ai.category_generator import (
    IndustryCategoryGenerator,
    fallback_categories,
    parse_categories_response,
)
from app.services.ai.exceptions import AICategorizationError
from app.services.ai.schemas import DEFAULT_TENANT_CATEGORIES


def test_parse_categories_from_object():
    content = '{"categories": ["Koszty serwerów", "Subskrypcje SaaS", "Wynagrodzenia", "Marketing", "Biuro", "Podatki", "Księgowość", "Szkolenia"]}'
    names = parse_categories_response(content)
    assert names[0] == "Koszty serwerów"
    assert len(names) >= 8


def test_parse_categories_from_raw_array():
    content = '["Materiały budowlane", "Robocizna", "Wynajem sprzętu", "Transport", "Ubezpieczenia", "Biuro", "Marketing", "Podatki"]'
    names = parse_categories_response(content)
    assert "Materiały budowlane" in names


def test_parse_categories_with_markdown_noise():
    content = (
        'Oto lista:\n```json\n'
        '{"categories": ["Koszt A", "Koszt B", "Koszt C", "Koszt D", '
        '"Koszt E", "Koszt F", "Koszt G", "Koszt H"]}\n```'
    )
    names = parse_categories_response(content)
    assert len(names) >= 8


def test_parse_categories_rejects_too_few():
    with pytest.raises(AICategorizationError):
        parse_categories_response('{"categories": ["Jedna"]}')


def test_fallback_categories_matches_defaults():
    assert fallback_categories() == list(DEFAULT_TENANT_CATEGORIES)


@pytest.mark.asyncio
async def test_generator_falls_back_on_short_industry():
    generator = IndustryCategoryGenerator()
    names = await generator.generate_categories("IT")
    assert names == list(DEFAULT_TENANT_CATEGORIES)
