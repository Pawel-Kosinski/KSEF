"""Testy potoku ETL – mock AI, bez Ollama."""

import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Invoice, InvoiceLine, Tenant, TenantCategory
from app.services.etl_pipeline import InvoiceEtlPipeline

FIXTURE = Path(__file__).parent / "fixtures" / "sample_fa3_invoice.xml"

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


class _FakeClassification(BaseModel):
    kategoria_glowna: str
    kategoria_podrzedna: str = "test"
    pewnosc_klasyfikacji: int = Field(default=80, ge=0, le=100)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_etl_pipeline_persists_lines_with_mock_ai(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(
        Tenant(
            id=tenant_id,
            name="Test Sp. z o.o.",
            nip="9876543210",
        )
    )
    db_session.add(
        TenantCategory(
            tenant_id=tenant_id,
            name="Materiały i Surowce",
            sort_order=1,
        )
    )
    db_session.add(
        TenantCategory(
            tenant_id=tenant_id,
            name="Paliwa i Transport",
            sort_order=2,
        )
    )
    await db_session.commit()

    mock_categorizer = MagicMock()
    mock_categorizer.classify_product_name = AsyncMock(
        side_effect=[
            _FakeClassification(kategoria_glowna="Materiały i Surowce"),
            _FakeClassification(kategoria_glowna="Paliwa i Transport"),
        ]
    )

    pipeline = InvoiceEtlPipeline(categorizer=mock_categorizer)
    xml_bytes = FIXTURE.read_bytes()

    result = await pipeline.process_invoice_xml(
        tenant_id,
        xml_bytes,
        session=db_session,
    )

    assert result.lines_processed == 2
    assert result.categories_used == ["Materiały i Surowce", "Paliwa i Transport"]
    assert mock_categorizer.classify_product_name.await_count == 2

    first_call = mock_categorizer.classify_product_name.await_args_list[0]
    assert first_call.args[0] == "Elektrody spawalnicze 3.2mm"
    assert first_call.kwargs["allowed_categories"] == [
        "Materiały i Surowce",
        "Paliwa i Transport",
    ]

    rows = (
        await db_session.execute(
            select(InvoiceLine).where(InvoiceLine.invoice_id == result.invoice_id)
        )
    ).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_etl_pipeline_respects_invoice_role_with_external_session(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1111111111"))
    db_session.add(
        TenantCategory(tenant_id=tenant_id, name="Materiały i Surowce", sort_order=1)
    )
    await db_session.commit()

    mock_categorizer = MagicMock()
    mock_categorizer.classify_product_name = AsyncMock(
        return_value=_FakeClassification(kategoria_glowna="Materiały i Surowce")
    )
    pipeline = InvoiceEtlPipeline(categorizer=mock_categorizer)
    xml_bytes = FIXTURE.read_bytes()

    result = await pipeline.process_invoice_xml(
        tenant_id,
        xml_bytes,
        ksef_number="KSEF-ROLE-TEST",
        invoice_role="sales",
        session=db_session,
    )

    invoice = (
        await db_session.execute(select(Invoice).where(Invoice.id == result.invoice_id))
    ).scalar_one()
    assert invoice.invoice_role == "sales"
    assert invoice.contractor_name == "Nabywca Testowy Sp. z o.o."
    assert invoice.total_net == Decimal("500.00")
    assert invoice.total_gross == Decimal("615.00")


@pytest.mark.asyncio
async def test_etl_pipeline_skips_duplicate_ksef_and_updates_role(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1111111111"))
    db_session.add(
        TenantCategory(tenant_id=tenant_id, name="Materiały i Surowce", sort_order=1)
    )
    await db_session.commit()

    mock_categorizer = MagicMock()
    mock_categorizer.classify_product_name = AsyncMock(
        return_value=_FakeClassification(kategoria_glowna="Materiały i Surowce")
    )
    pipeline = InvoiceEtlPipeline(categorizer=mock_categorizer)
    xml_bytes = FIXTURE.read_bytes()
    ksef_number = "KSEF-DUP-TEST"

    await pipeline.process_invoice_xml(
        tenant_id,
        xml_bytes,
        ksef_number=ksef_number,
        invoice_role="cost",
        session=db_session,
    )
    second = await pipeline.process_invoice_xml(
        tenant_id,
        xml_bytes,
        ksef_number=ksef_number,
        invoice_role="sales",
        session=db_session,
    )

    invoices = (
        await db_session.execute(select(Invoice).where(Invoice.ksef_number == ksef_number))
    ).scalars().all()
    assert len(invoices) == 1
    assert invoices[0].invoice_role == "sales"
    assert mock_categorizer.classify_product_name.await_count == 2
    assert second.lines_processed == 2
