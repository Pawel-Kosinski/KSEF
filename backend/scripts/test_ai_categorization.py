#!/usr/bin/env python
"""
Test kategoryzacji AI z dynamicznymi kategoriami tenanta.

Użycie:
  python scripts/test_ai_categorization.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai import DEFAULT_TENANT_CATEGORIES, ProductCategorizer
from app.services.ai.exceptions import AICategorizerError

SAMPLE_PRODUCTS = [
    "ON BP",
    "Karton fasonowy 300x200",
    "Usługa programistyczna",
]

CUSTOM_CATEGORIES = [
    "Surowce produkcyjne",
    "Logistyka i paliwa",
    "IT i oprogramowanie",
    "Inne",
]


async def main() -> int:
    categorizer = ProductCategorizer()
    categories = list(DEFAULT_TENANT_CATEGORIES)
    print(f"Ollama: {categorizer._host} | model: {categorizer._model}")
    print(f"Kategorie: {categories}\n")

    for name in SAMPLE_PRODUCTS:
        print(f"Produkt: {name!r}")
        try:
            result = await categorizer.classify_product_name(
                name,
                allowed_categories=categories,
            )
            print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
        except AICategorizerError as exc:
            print(f"  BLAD: {exc}", file=sys.stderr)
            return 1
        print()

    print("--- Test z wlasnym drzewem kategorii ---")
    for name in SAMPLE_PRODUCTS[:1]:
        result = await categorizer.classify_product_name(
            name,
            allowed_categories=CUSTOM_CATEGORIES,
        )
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
