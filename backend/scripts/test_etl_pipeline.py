#!/usr/bin/env python
"""
Test potoku ETL: XML -> AI -> PostgreSQL (RLS).

Wymaga działającego PostgreSQL, Ollama oraz istniejącego tenanta.
Tworzy tenanta testowego, jeśli nie istnieje.

Użycie:
  python scripts/test_etl_pipeline.py
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database.models import InvoiceLine, Tenant, TenantCategory
from app.database.session import async_session_factory, set_tenant_context
from app.services.ai.schemas import DEFAULT_TENANT_CATEGORIES
from app.services.etl_pipeline import InvoiceEtlPipeline

FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_fa3_invoice.xml"
TEST_NIP = "9998887776"


async def ensure_test_tenant(session) -> uuid.UUID:
    result = await session.execute(select(Tenant).where(Tenant.nip == TEST_NIP))
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant.id

    tenant_id = uuid.uuid4()
    session.add(
        Tenant(
            id=tenant_id,
            name="ETL Test Tenant",
            nip=TEST_NIP,
        )
    )
    for idx, name in enumerate(DEFAULT_TENANT_CATEGORIES, start=1):
        session.add(
            TenantCategory(
                tenant_id=tenant_id,
                name=name,
                sort_order=idx,
            )
        )
    await session.flush()
    return tenant_id


async def main() -> int:
    pipeline = InvoiceEtlPipeline()
    xml_bytes = FIXTURE.read_bytes()

    async with async_session_factory() as session:
        await session.begin()
        tenant_id = await ensure_test_tenant(session)
        await set_tenant_context(session, tenant_id)

        result = await pipeline.process_invoice_xml(
            tenant_id,
            xml_bytes,
            ksef_number=f"ETL-TEST-{uuid.uuid4().hex[:8]}",
            session=session,
        )
        await session.commit()

    print(f"tenant_id: {result.tenant_id}")
    print(f"invoice_id: {result.invoice_id}")
    print(f"lines_processed: {result.lines_processed}")
    print(f"categories_used: {result.categories_used}")

    async with async_session_factory() as session:
        await session.begin()
        await set_tenant_context(session, tenant_id)
        rows = (
            await session.execute(
                select(InvoiceLine).where(InvoiceLine.invoice_id == result.invoice_id)
            )
        ).scalars().all()
        await session.commit()

    for row in rows:
        print(
            f"  [{row.line_number}] {row.product_name!r} -> "
            f"{row.ai_category_main} / {row.ai_category_sub} ({row.ai_confidence}%)"
        )

    print()
    print("Token JWT dla dashboardu (NIP testowy 9998887776):")
    print(f"  python scripts/create_dev_token.py --nip {TEST_NIP}")
    print()
    print("Następnie wklej token do frontend/.env.local i zrestartuj npm run dev.")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
