#!/usr/bin/env python
"""
Test parsowania lokalnego pliku XML FA(3).

Użycie:
  python scripts/test_parse_fa3_xml.py
  python scripts/test_parse_fa3_xml.py ścieżka/do/faktury.xml
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

# Umożliwia import app.* przy uruchomieniu z katalogu backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.xml import Fa3XmlParserError, parse_fa3_xml_file


def _json_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Nieobsługiwany typ: {type(obj)}")


def main() -> int:
    default_fixture = (
        Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_fa3_invoice.xml"
    )
    xml_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_fixture

    print(f"Parsowanie: {xml_path}")
    try:
        result = parse_fa3_xml_file(xml_path)
    except Fa3XmlParserError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1

    print(f"Namespace: {result.namespace}")
    print(f"Liczba wierszy: {len(result.lines)}")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
