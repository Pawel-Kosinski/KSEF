"""
Generator kategorii kosztowych/przychodowych na podstawie branży (Smart Onboarding).

Odporny na błędy parsowania JSON – wielopoziomowy fallback do domyślnych kategorii MVP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from ollama import Client

from app.config import Settings, get_settings
from app.services.ai.exceptions import AICategorizationError
from app.services.ai.schemas import DEFAULT_TENANT_CATEGORIES

logger = logging.getLogger(__name__)

_MIN_CATEGORIES = 8
_MAX_CATEGORIES = 15
_MAX_NAME_LEN = 128

_JSON_ARRAY_PATTERN = re.compile(r"\[[\s\S]*?\]")
_CATEGORY_CLEANUP = re.compile(r"[^\w\sąćęłńóśźżĄĆĘŁŃÓŚŹŻ&./\-()]")

_CATEGORIES_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "categories": {
            "type": "array",
            "items": {"type": "string", "minLength": 2, "maxLength": _MAX_NAME_LEN},
            "minItems": _MIN_CATEGORIES,
            "maxItems": _MAX_CATEGORIES,
        }
    },
    "required": ["categories"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = """\
Jesteś ekspertem finansowym dla polskich MŚP (system "Wirtualny CFO").
Na podstawie opisu branży firmy wygeneruj listę kategorii kosztowych i przychodowych dopasowanych do tej działalności.

Wymagania:
- 10–15 pozycji po polsku, konkretnych dla branży (np. software house: "Koszty serwerów", firma budowlana: "Materiały budowlane").
- Mieszaj koszty i przychody tam, gdzie ma to sens dla danej branży.
- Nie używaj ogólników typu "Inne" jako jedynej pozycji.
- Odpowiedź to wyłącznie poprawny JSON (bez Markdown) w formacie:
{"categories": ["Kategoria 1", "Kategoria 2", ...]}\
"""


def _sanitize_category_name(value: str) -> str | None:
    cleaned = _CATEGORY_CLEANUP.sub("", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 2:
        return None
    return cleaned[:_MAX_NAME_LEN]


def _dedupe_preserve_order(names: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
    return result


def _extract_categories_from_parsed(data: Any) -> list[str] | None:
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        for key in ("categories", "kategorie", "category_names", "items"):
            if key in data and isinstance(data[key], list):
                raw_items = data[key]
                break
        else:
            return None
    else:
        return None

    names: list[str] = []
    for item in raw_items:
        if isinstance(item, str):
            sanitized = _sanitize_category_name(item)
            if sanitized:
                names.append(sanitized)
        elif isinstance(item, dict):
            for field in ("name", "category", "kategoria"):
                if field in item and isinstance(item[field], str):
                    sanitized = _sanitize_category_name(item[field])
                    if sanitized:
                        names.append(sanitized)
                    break

    names = _dedupe_preserve_order(names)
    if len(names) < _MIN_CATEGORIES:
        return None
    return names[:_MAX_CATEGORIES]


def _strip_markdown_fences(text: str) -> str:
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return text


def parse_categories_response(content: str) -> list[str]:
    """Parsuje odpowiedź modelu – rzuca AICategorizationError gdy brak sensownej listy."""
    text = _strip_markdown_fences(content.strip())
    if not text:
        raise AICategorizationError("Pusta odpowiedź modelu")

    try:
        parsed = json.loads(text)
        names = _extract_categories_from_parsed(parsed)
        if names:
            return names
    except json.JSONDecodeError:
        pass

    for match in _JSON_ARRAY_PATTERN.finditer(text):
        try:
            parsed = json.loads(match.group())
            names = _extract_categories_from_parsed(parsed)
            if names:
                return names
        except json.JSONDecodeError:
            continue

    for match in re.finditer(r"\{[\s\S]*\}", text):
        try:
            parsed = json.loads(match.group())
            names = _extract_categories_from_parsed(parsed)
            if names:
                return names
        except json.JSONDecodeError:
            continue

    raise AICategorizationError(f"Nie udało się wyciągnąć tablicy kategorii z: {text[:200]!r}")


def _merge_with_defaults(generated: list[str]) -> list[str]:
    merged = _dedupe_preserve_order(generated)
    for default in DEFAULT_TENANT_CATEGORIES:
        if len(merged) >= _MAX_CATEGORIES:
            break
        if default.casefold() not in {name.casefold() for name in merged}:
            merged.append(default)
    return merged[:_MAX_CATEGORIES]


def fallback_categories() -> list[str]:
    return list(DEFAULT_TENANT_CATEGORIES)


def _ollama_generate_sync(
    host: str,
    model: str,
    industry: str,
) -> str:
    client = Client(host=host)
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Branża / opis działalności firmy:\n{industry.strip()}\n\n"
                    "Zwróć JSON z tablicą categories."
                ),
            },
        ],
        format=_CATEGORIES_JSON_SCHEMA,
        options={"temperature": 0.3, "num_predict": 512},
    )
    return response.message.content or ""


class IndustryCategoryGenerator:
    """Generuje listę kategorii tenanta na podstawie opisu branży."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        settings: Settings | None = None,
        client: Client | None = None,
    ):
        self._settings = settings or get_settings()
        self._host = host or self._settings.ollama_host
        self._model = model or self._settings.ollama_model
        self._sync_client = client

    async def generate_categories(self, industry: str) -> list[str]:
        cleaned_industry = industry.strip()
        if len(cleaned_industry) < 3:
            logger.warning("Zbyt krótki opis branży – używam domyślnych kategorii")
            return fallback_categories()

        timeout = self._settings.ollama_timeout_sec
        try:
            content = await asyncio.wait_for(
                self._call_ollama(cleaned_industry),
                timeout=timeout,
            )
            names = parse_categories_response(content)
            return _merge_with_defaults(names)
        except (asyncio.TimeoutError, AICategorizationError, Exception) as exc:
            logger.warning(
                "Generator kategorii AI nie powiódł się (branża=%r): %s – fallback",
                cleaned_industry[:80],
                exc,
            )
            return fallback_categories()

    async def _call_ollama(self, industry: str) -> str:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Branża / opis działalności firmy:\n{industry}\n\n"
                    "Zwróć JSON z tablicą categories."
                ),
            },
        ]
        try:
            if self._sync_client is not None:
                response = await asyncio.to_thread(
                    self._sync_client.chat,
                    model=self._model,
                    messages=messages,
                    format=_CATEGORIES_JSON_SCHEMA,
                    options={"temperature": 0.3, "num_predict": 512},
                )
                return response.message.content or ""
            return await asyncio.to_thread(
                _ollama_generate_sync,
                self._host,
                self._model,
                industry,
            )
        except Exception as exc:
            raise AICategorizationError(
                f"Błąd wywołania Ollama ({self._host}, model={self._model}): {exc}"
            ) from exc


async def generate_categories_for_industry(industry: str) -> list[str]:
    generator = IndustryCategoryGenerator()
    return await generator.generate_categories(industry)
