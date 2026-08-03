#!/usr/bin/env python
"""
Test uwierzytelniania KSeF 2.0 tokenem systemowym.

Wymaga zmiennych środowiskowych (lub pliku .env):
  KSEF_BASE_URL  – np. https://api-test.ksef.mf.gov.pl/api/v2
  KSEF_NIP       – NIP kontekstu
  KSEF_TOKEN     – token wygenerowany w MCU

Użycie:
  python scripts/test_ksef_auth.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ksef import KsefAuthService
from app.services.ksef.exceptions import KsefError


async def main() -> int:
    print("Uwierzytelnianie KSeF 2.0 (token KSeF → accessToken)...")
    service = KsefAuthService()

    try:
        tokens = await service.authenticate_with_ksef_token()
    except KsefError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1

    print(f"referenceNumber: {tokens.reference_number}")
    print(f"accessToken (pierwsze 40 znaków): {tokens.access_token[:40]}...")
    print(f"accessToken ważny do: {tokens.access_token_valid_until}")
    print(f"refreshToken ważny do: {tokens.refresh_token_valid_until}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
