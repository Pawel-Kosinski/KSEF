"""
Serwis kategoryzacji wydatków – reguły kontrahentów + Ollama (Structured Output).

Kolejność: reguła NIP → LLM → fallback.
"""

import asyncio
import json
import re
import uuid
from typing import Any

from ollama import Client
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.services.ai.classification_result import ClassificationResult
from app.services.ai.exceptions import AIInputIsolationError, AICategorizationError
from app.services.ai.schemas import (
    build_category_json_schema,
    build_category_schema,
    validate_allowed_categories,
)
from app.services.contractor_rules import get_contractor_rule

_SYSTEM_PROMPT_TEMPLATE = """\
Jesteś precyzyjnym silnikiem kategoryzującym dla systemu finansowego MŚP ("Wirtualny CFO").
Analizujesz wyłącznie nazwę towaru lub usługi (pole P_7) z polskiej faktury kosztowej.

Dozwolone kategorie główne (JSON):
{categories_json}

Musisz wybrać JEDNĄ kategorię główną z podanej listy. Nie wolno ci wymyślać własnych nazw.
Pole kategoria_podrzedna: maksymalnie 3 słowa po polsku (np. "Olej napędowy", "Hosting www").

Odpowiedź to wyłącznie poprawny JSON (bez Markdown), np.:
{{"kategoria_glowna": "{example_category}", "kategoria_podrzedna": "Przykład", "pewnosc_klasyfikacji": 92}}

Skoncentruj się na znaczeniu słów i polskim żargonie księgowym (np. "ON" = olej napędowy).\
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
    categories_json = json.dumps(categories, ensure_ascii=False)
    example_category = categories[0]
    return _SYSTEM_PROMPT_TEMPLATE.format(
        categories_json=categories_json,
        example_category=example_category,
    )


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
    sub = str(data.get("kategoria_podrzedna", data.get("category_sub", "")))
    sub = re.split(r"['\"{}\[\]<>\\]", sub)[0]
    sub = _SUBCATEGORY_CLEANUP.sub("", sub).strip()
    words = sub.split()[:3]
    data["kategoria_podrzedna"] = " ".join(words) if words else "Inne"

    main_raw = data.get("kategoria_glowna", data.get("category", ""))
    data["kategoria_glowna"] = _normalize_main_category(str(main_raw), allowed_categories)

    confidence_raw = data.get("pewnosc_klasyfikacji", data.get("confidence", 50))
    try:
        confidence = int(float(confidence_raw) * 100) if float(confidence_raw) <= 1 else int(confidence_raw)
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
    """Hybrydowy kategoryzator: reguły NIP + Ollama Structured Output."""

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
        *,
        session: AsyncSession | None = None,
        tenant_id: uuid.UUID | None = None,
        contractor_nip: str | None = None,
    ) -> ClassificationResult:
        categories = validate_allowed_categories(allowed_categories)

        if session is not None and tenant_id is not None and contractor_nip:
            rule = await get_contractor_rule(session, tenant_id, contractor_nip)
            if rule is not None and rule.category_main in categories:
                return ClassificationResult(
                    kategoria_glowna=rule.category_main,
                    kategoria_podrzedna=rule.category_sub or "Inne",
                    pewnosc_klasyfikacji=100,
                    source="rule",
                )

        ai_result = await self._classify_with_ai(product_name, categories)
        return ClassificationResult(
            kategoria_glowna=ai_result.kategoria_glowna,
            kategoria_podrzedna=ai_result.kategoria_podrzedna,
            pewnosc_klasyfikacji=ai_result.pewnosc_klasyfikacji,
            source="ai",
        )

    async def _classify_with_ai(
        self,
        product_name: str,
        allowed_categories: list[str],
    ) -> BaseModel:
        safe_name = _assert_product_name_isolation(product_name)
        schema_cls = build_category_schema(allowed_categories)
        json_schema = build_category_json_schema(allowed_categories)
        system_prompt = build_system_prompt(allowed_categories)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Sklasyfikuj pozycję faktury. Zwróć JSON zgodny ze schematem.\n"
                    f"Pozycja: {safe_name}"
                ),
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
            return _parse_category_response(content, schema_cls, allowed_categories)
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
    return {
        "kategoria_glowna": result.kategoria_glowna,
        "kategoria_podrzedna": result.kategoria_podrzedna,
        "pewnosc_klasyfikacji": result.pewnosc_klasyfikacji,
        "source": result.source,
    }
