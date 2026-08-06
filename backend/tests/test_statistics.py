"""Testy serwisu statystyk – PostgreSQL (date_trunc)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Invoice, InvoiceLine, Tenant
from app.database.session import set_tenant_context
from app.services.analytics.statistics import StatisticsService

TEST_DB_URL = "postgresql+asyncpg://vcfo:vcfo_secret@localhost:5432/wirtualny_cfo"


@pytest_asyncio.fixture
async def stats_session():
    engine = create_async_engine(TEST_DB_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    tenant_id = uuid.uuid4()
    test_nip = str(tenant_id.int % 9_000_000_000 + 1_000_000_000)
    invoice_jan_id = uuid.uuid4()
    invoice_feb_id = uuid.uuid4()
    invoice_sales_id = uuid.uuid4()

    async with factory() as session:
        await set_tenant_context(session, tenant_id)
        session.add_all(
            [
                Tenant(id=tenant_id, name="Stats Test", nip=test_nip),
                Invoice(
                    id=invoice_jan_id,
                    tenant_id=tenant_id,
                    invoice_number="FV/01/2026",
                    issue_date=date(2026, 1, 15),
                    seller_nip="5265877635",
                    buyer_nip=test_nip,
                    invoice_role="cost",
                ),
                Invoice(
                    id=invoice_feb_id,
                    tenant_id=tenant_id,
                    invoice_number="FV/02/2026",
                    issue_date=date(2026, 2, 10),
                    seller_nip="9876543210",
                    buyer_nip=test_nip,
                    invoice_role="cost",
                ),
                Invoice(
                    id=invoice_sales_id,
                    tenant_id=tenant_id,
                    invoice_number="FV/S/01/2026",
                    issue_date=date(2026, 1, 20),
                    seller_nip=test_nip,
                    buyer_nip="1111111111",
                    invoice_role="sales",
                ),
                InvoiceLine(
                    tenant_id=tenant_id,
                    invoice_id=invoice_jan_id,
                    line_number=1,
                    product_name="Olej ON",
                    quantity=Decimal("100"),
                    unit_price=Decimal("2.50"),
                    line_net_value=Decimal("250.00"),
                    ai_category_main="Paliwa i Transport",
                ),
                InvoiceLine(
                    tenant_id=tenant_id,
                    invoice_id=invoice_jan_id,
                    line_number=2,
                    product_name="Karton",
                    quantity=Decimal("10"),
                    unit_price=Decimal("25.00"),
                    line_net_value=Decimal("250.00"),
                    ai_category_main="Opakowania",
                ),
                InvoiceLine(
                    tenant_id=tenant_id,
                    invoice_id=invoice_feb_id,
                    line_number=1,
                    product_name="IT support",
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000.00"),
                    line_net_value=Decimal("1000.00"),
                    ai_category_main="Koszty Biurowe i IT",
                ),
                InvoiceLine(
                    tenant_id=tenant_id,
                    invoice_id=invoice_sales_id,
                    line_number=1,
                    product_name="Usługa consulting",
                    quantity=Decimal("1"),
                    unit_price=Decimal("300.00"),
                    line_net_value=Decimal("300.00"),
                    ai_category_main="Usługi",
                ),
            ]
        )
        await session.commit()

    async with factory() as session:
        await set_tenant_context(session, tenant_id)
        yield session, tenant_id

    async with factory() as session:
        await set_tenant_context(session, tenant_id)
        await session.execute(
            InvoiceLine.__table__.delete().where(InvoiceLine.tenant_id == tenant_id)
        )
        await session.execute(
            Invoice.__table__.delete().where(Invoice.tenant_id == tenant_id)
        )
        await session.execute(Tenant.__table__.delete().where(Tenant.id == tenant_id))
        await session.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_cost_structure_aggregation(stats_session):
    session, tenant_id = stats_session
    await set_tenant_context(session, tenant_id)
    service = StatisticsService(session, tenant_id)

    result = await service.get_structure(role="cost")

    assert result.total_net == Decimal("1500.00")
    categories = {item.category: item.total_net for item in result.items}
    assert categories["Paliwa i Transport"] == Decimal("250.00")
    assert categories["Opakowania"] == Decimal("250.00")
    assert categories["Koszty Biurowe i IT"] == Decimal("1000.00")


@pytest.mark.asyncio
async def test_trend_monthly_aggregation(stats_session):
    session, tenant_id = stats_session
    await set_tenant_context(session, tenant_id)
    service = StatisticsService(session, tenant_id)

    result = await service.get_trend(role="cost")

    assert len(result.items) == 2
    assert result.items[0].period == "2026-01"
    assert result.items[0].total_net == Decimal("500.00")
    assert result.items[1].period == "2026-02"
    assert result.items[1].total_net == Decimal("1000.00")
    assert result.granularity == "month"


@pytest.mark.asyncio
async def test_top_vendors_limit(stats_session):
    session, tenant_id = stats_session
    await set_tenant_context(session, tenant_id)
    service = StatisticsService(session, tenant_id)

    result = await service.get_top_counterparties(role="cost", limit=5)

    assert len(result.items) == 2
    assert result.items[0].counterparty_nip == "9876543210"
    assert result.items[0].total_net == Decimal("1000.00")
    assert result.items[0].rank == 1


@pytest.mark.asyncio
async def test_date_filter_excludes_out_of_range(stats_session):
    session, tenant_id = stats_session
    await set_tenant_context(session, tenant_id)
    service = StatisticsService(session, tenant_id)

    result = await service.get_structure(
        role="cost",
        date_from=date(2026, 2, 1),
        date_to=date(2026, 2, 28),
    )

    assert result.total_net == Decimal("1000.00")
    assert len(result.items) == 1
    assert result.items[0].category == "Koszty Biurowe i IT"


@pytest.mark.asyncio
async def test_trend_category_filter_respects_role(stats_session):
    session, tenant_id = stats_session
    await set_tenant_context(session, tenant_id)
    service = StatisticsService(session, tenant_id)

    cost_it = await service.get_trend(role="cost", category="Koszty Biurowe i IT")
    sales_uslugi = await service.get_trend(role="sales", category="Usługi")

    assert cost_it.total_net == Decimal("1000.00")
    assert cost_it.role == "cost"
    assert cost_it.category == "Koszty Biurowe i IT"

    assert sales_uslugi.total_net == Decimal("300.00")
    assert sales_uslugi.role == "sales"
    assert sales_uslugi.category == "Usługi"

    # Ta sama nazwa kategorii w innym role nie zwraca danych drugiej strony
    cost_uslugi = await service.get_trend(role="cost", category="Usługi")
    assert cost_uslugi.total_net == Decimal("0")

    sales_it = await service.get_trend(role="sales", category="Koszty Biurowe i IT")
    assert sales_it.total_net == Decimal("0")


@pytest.mark.asyncio
async def test_cashflow_combined_aggregation(stats_session):
    session, tenant_id = stats_session
    await set_tenant_context(session, tenant_id)
    service = StatisticsService(session, tenant_id)

    result = await service.get_cashflow()

    assert result.granularity == "month"
    assert len(result.items) == 2

    jan = result.items[0]
    assert jan.date == "2026-01"
    assert jan.sales == Decimal("300.00")
    assert jan.costs == Decimal("500.00")
    assert jan.balance == Decimal("-200.00")

    feb = result.items[1]
    assert feb.date == "2026-02"
    assert feb.sales == Decimal("0")
    assert feb.costs == Decimal("1000.00")
    assert feb.balance == Decimal("-1000.00")

    assert result.total_sales == Decimal("300.00")
    assert result.total_costs == Decimal("1500.00")
    assert result.total_balance == Decimal("-1200.00")
