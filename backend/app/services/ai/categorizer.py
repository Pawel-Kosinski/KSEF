"""
Serwis kategoryzacji wydatków – Ollama + dynamiczne Structured Outputs per tenant.

Wywołania Ollama (GPU inference) są delegowane do puli wątków via asyncio.to_thread(),
aby nie blokować event loopa FastAPI.
"""

import asyncio
import json
import re
from typing import Any

from ollama import Client
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.ai.exceptions import AIInputIsolationError, AICategorizationError
from app.services.ai.schemas import (
    build_category_json_schema,
    build_category_schema,
    get_category_literal_values,
    validate_allowed_categories,
)

_SYSTEM_PROMPT_TEMPLATE = """\
Jesteś precyzyjnym silnikiem kategoryzującym dla systemu finansowego MŚP ("Wirtualny CFO").
Twoim wyłącznym zadaniem jest analiza pojedynczych, surowych nazw towarów lub usług \
pobranych z polskich faktur kosztowych i przypisanie ich do właściwych węzłów z dostępnego \
drzewa kategorii.
Dostępne kategorie główne (wybierz dokładnie jedną – nie wolno używać innych nazw):
{categories_block}
Pole kategoria_podrzedna: maksymalnie 3 słowa po polsku.
Skoncentruj się na znaczeniu słów, wykrywaj typowy polski żargon księgowy i skróty \
(np. "ON" to Olej Napędowy, "F-vat" to prowizja itp.).
Jesteś zintegrowany maszynowo, więc twoja odpowiedź to zawsze i wyłącznie czysty JSON, \
bez wstępów, tłumaczeń ani znaczników Markdown.\
"""

_NIP_PATTERN = re.compile(r"\b\d{10}\b")
_AMOUNT_PATTERN = re.compile(
    r"(?:"
    r"\b\d{1,3}(?:[ \u00a0]\d{3})+[.,]\d{2}"
    r"|\b\d+[.,]\d{2}"
    r")\s*(?:zł|pln|eur|usd)?\b",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
_SUBCATEGORY_CLEANUP = re.compile(r"[^\w\sąćęłńóśźżĄĆĘŁŃÓŚŹŻ.-]")


def build_system_prompt(allowed_categories: list[str]) -> str:
    categories = validate_allowed_categories(allowed_categories)
    categories_block = "\n".join(f"- {name}" for name in categories)
    return _SYSTEM_PROMPT_TEMPLATE.format(categories_block=categories_block)


def _normalize_main_category(value: str, allowed_categories: list[str]) -> str:
    if value in allowed_categories:
        return value
    lowered = value.lower()
    for category in allowed_categories:
        if category.lower() == lowered:
            return category
    for category in allowed_categories:
        if category.lower() in lowered or lowered in category.lower():
            return category
    return allowed_categories[0]


def _sanitize_model_payload(data: dict, allowed_categories: list[str]) -> dict:
    sub = str(data.get("kategoria_podrzedna", ""))
    sub = re.split(r"['\"{}\[\]<>\\]", sub)[0]
    sub = _SUBCATEGORY_CLEANUP.sub("", sub).strip()
    words = sub.split()[:3]
    data["kategoria_podrzedna"] = " ".join(words) if words else "Inne"

    data["kategoria_glowna"] = _normalize_main_category(
        str(data.get("kategoria_glowna", "")),
        allowed_categories,
    )

    try:
        confidence = int(data.get("pewnosc_klasyfikacji", 50))
    except (TypeError, ValueError):
        confidence = 50
    data["pewnosc_klasyfikacji"] = max(0, min(100, confidence))
    return data


def _parse_category_response(
    content: str,
    schema_cls: type[BaseModel],
    allowed_categories: list[str],
) -> BaseModel:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_PATTERN.search(content)
        if not match:
            raise AICategorizationError(f"Brak poprawnego JSON w odpowiedzi: {content!r}")
        data = json.loads(match.group())

    if not isinstance(data, dict):
        raise AICategorizationError(f"Oczekiwano obiektu JSON, otrzymano: {type(data)}")

    payload = _sanitize_model_payload(data, allowed_categories)
    return schema_cls.model_validate(payload)


def _assert_product_name_isolation(product_name: str) -> str:
    cleaned = product_name.strip()
    if not cleaned:
        raise AIInputIsolationError("product_name nie może być pusty")
    if len(cleaned) > 512:
        raise AIInputIsolationError("product_name przekracza limit 512 znaków (P_7 FA(3))")
    if _NIP_PATTERN.search(cleaned):
        raise AIInputIsolationError("product_name nie może zawierać numeru NIP")
    if _AMOUNT_PATTERN.search(cleaned):
        raise AIInputIsolationError("product_name nie może zawierać kwot pieniężnych")
    if _EMAIL_PATTERN.search(cleaned):
        raise AIInputIsolationError("product_name nie może zawierać adresu e-mail")
    return cleaned


def _ollama_chat_sync(
    host: str,
    model: str,
    messages: list[dict[str, str]],
    json_schema: dict[str, Any],
) -> str:
    """Synchroniczne wywołanie Ollama – uruchamiane w asyncio.to_thread()."""
    client = Client(host=host)
    response = client.chat(
        model=model,
        messages=messages,
        format=json_schema,
        options={
            "temperature": 0.0,
            "num_predict": 128,
        },
    )
    return response.message.content or ""


class ProductCategorizer:
    """Klient Ollama – kategorie definiowane per tenant; inference w puli wątków."""

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

    async def classify_product_name(
        self,
        product_name: str,
        allowed_categories: list[str],
    ) -> BaseModel:
        """
        Kategoryzuje nazwę towaru/usługi (P_7) względem drzewa kategorii tenanta.

        Do modelu trafia wyłącznie product_name – bez NIP, kwot ani metadanych faktury.
        """
        categories = validate_allowed_categories(allowed_categories)
        safe_name = _assert_product_name_isolation(product_name)
        schema_cls = build_category_schema(categories)
        json_schema = build_category_json_schema(categories)
        system_prompt = build_system_prompt(categories)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Sklasyfikuj następującą pozycję z faktury: {safe_name}",
            },
        ]

        try:
            if self._sync_client is not None:
                response = await asyncio.to_thread(
                    self._sync_client.chat,
                    model=self._model,
                    messages=messages,
                    format=json_schema,
                    options={"temperature": 0.0, "num_predict": 128},
                )
                content = response.message.content or ""
            else:
                content = await asyncio.to_thread(
                    _ollama_chat_sync,
                    self._host,
                    self._model,
                    messages,
                    json_schema,
                )
        except Exception as exc:
            raise AICategorizationError(
                f"Błąd wywołania Ollama ({self._host}, model={self._model}): {exc}"
            ) from exc

        if not content:
            raise AICategorizationError("Ollama zwróciła pustą odpowiedź")

        try:
            return _parse_category_response(content, schema_cls, categories)
        except AICategorizationError:
            raise
        except Exception as exc:
            raise AICategorizationError(
                f"Odpowiedź modelu nie przeszła walidacji Pydantic: {content!r}"
            ) from exc


async def classify_product_name(
    product_name: str,
    allowed_categories: list[str],
) -> dict[str, Any]:
    categorizer = ProductCategorizer()
    result = await categorizer.classify_product_name(product_name, allowed_categories)
    return result.model_dump()
