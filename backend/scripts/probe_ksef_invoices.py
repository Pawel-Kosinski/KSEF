#!/usr/bin/env python
"""Diagnostika: ile faktur KSeF widzi dla NIP (metadata + eksport)."""

import asyncio
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.config import get_settings
from app.services.ksef.auth import KsefAuthService
from app.services.ksef.client import KsefClient
from app.services.ksef.crypto import build_export_encryption_material
from app.services.ksef.models import (
    ExportDateRange,
    ExportEncryptionInfo,
    ExportFilters,
    InvoiceExportRequest,
)

try:
    WARSAW_TZ = ZoneInfo("Europe/Warsaw")
except Exception:
    WARSAW_TZ = timezone(timedelta(hours=1))


async def query_metadata(
    client: KsefClient,
    access_token: str,
    nip: str,
    subject_type: str,
    date_from: date,
    date_to: date,
    date_type: str,
) -> dict | None:
    start = datetime.combine(date_from, time.min, tzinfo=WARSAW_TZ)
    end = datetime.combine(date_to, time(23, 59, 59), tzinfo=WARSAW_TZ)
    body = {
        "queryCriteria": {
            "subjectType": subject_type,
            "dateRange": {
                "dateType": date_type,
                "from": start.isoformat(),
                "to": end.isoformat(),
            },
        }
    }
    settings = get_settings()
    url = f"{settings.ksef_base_url.rstrip('/')}/invoices/query/metadata"
    async with httpx.AsyncClient(timeout=30.0) as http:
        response = await http.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=body,
        )
    print(f"  metadata {subject_type} {date_type} {date_from}..{date_to} -> HTTP {response.status_code}")
    if response.status_code != 200:
        print(f"    {response.text[:300]}")
        return None
    data = response.json()
    count = len(data.get("invoices", []) or [])
    has_more = data.get("hasMore", False)
    print(f"    invoices={count} hasMore={has_more}")
    for inv in (data.get("invoices") or [])[:3]:
        print(f"    - ksef={inv.get('ksefNumber')} issue={inv.get('issueDate')}")
    return data


async def probe_export_count(
    client: KsefClient,
    access_token: str,
    subject_type: str,
    date_from: date,
    date_to: date,
) -> int:
    certs = await client.get_public_key_certificates()
    material = build_export_encryption_material(certs)
    start = datetime.combine(date_from, time.min, tzinfo=WARSAW_TZ)
    end = datetime.combine(date_to, time(23, 59, 59), tzinfo=WARSAW_TZ)
    request = InvoiceExportRequest(
        encryption=ExportEncryptionInfo(
            encrypted_symmetric_key=material.encrypted_symmetric_key_b64,
            initialization_vector=material.initialization_vector_b64,
            public_key_id=material.public_key_id,
        ),
        filters=ExportFilters(
            subject_type=subject_type,
            date_range=ExportDateRange(
                date_type="Issue",
                from_=start.isoformat(),
                to=end.isoformat(),
            ),
        ),
        only_metadata=True,
    )
    init = await client.start_invoice_export(access_token, request)
    ref = init.reference_number
    for _ in range(60):
        status = await client.get_export_status(ref, access_token)
        if status.status.code == 200:
            pkg = status.package
            count = pkg.invoice_count if pkg else 0
            print(f"  export {subject_type} Issue -> count={count}")
            return count
        if status.status.code != 100:
            print(f"  export failed: {status.status}")
            return -1
        await asyncio.sleep(1)
    print("  export timeout")
    return -1


async def main() -> int:
    settings = get_settings()
    nip = settings.ksef_nip or "1186638420"
    print(f"KSeF base: {settings.ksef_base_url}")
    print(f"NIP kontekstu: {nip}")
    print(f"Token KSeF: {'OK' if settings.ksef_token else 'BRAK'}")

    auth = KsefAuthService()
    tokens = await auth.authenticate_with_ksef_token(nip=nip)
    client = KsefClient()
    access = tokens.access_token

    today = date.today()
    week_ago = today - timedelta(days=7)

    print("\n=== Query metadata ===")
    for subject in ("Subject1", "Subject2"):
        for date_type in ("Issue", "PermanentStorage"):
            await query_metadata(client, access, nip, subject, week_ago, today, date_type)

    print("\n=== Export (metadata only) ===")
    for subject in ("Subject1", "Subject2"):
        await probe_export_count(client, access, subject, week_ago, today)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
