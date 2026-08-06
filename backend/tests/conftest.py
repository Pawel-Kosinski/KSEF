"""Wspólne fixtury testów integracyjnych (PostgreSQL)."""

import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.models import Invoice, InvoiceLine, Tenant, TenantCategory
from app.database.session import async_session_factory, engine, set_tenant_context
from app.main import app
from app.services.auth_service import create_access_token


@pytest_asyncio.fixture(autouse=True)
async def dispose_async_engine_after_test():
    """Zamyka pulę połączeń asyncpg między testami (Windows / pytest-asyncio)."""
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def api_tenant_session():
    """Tenant z danymi testowymi + klient HTTP z tokenem JWT."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    test_nip = str(tenant_id.int % 9_000_000_000 + 1_000_000_000)
    invoice_cost_id = uuid.uuid4()
    invoice_sales_id = uuid.uuid4()

    async with async_session_factory() as session:
        await session.begin()
        await set_tenant_context(session, tenant_id)
        session.add_all(
            [
                Tenant(id=tenant_id, name="API Test", nip=test_nip),
                TenantCategory(tenant_id=tenant_id, name="IT", sort_order=1),
                TenantCategory(tenant_id=tenant_id, name="Transport", sort_order=2),
                Invoice(
                    id=invoice_cost_id,
                    tenant_id=tenant_id,
                    invoice_number="FV/C/01",
                    issue_date=date(2026, 3, 1),
                    seller_nip="1111111111",
                    buyer_nip=test_nip,
                    invoice_role="cost",
                    total_net=Decimal("100.00"),
                    total_vat=Decimal("23.00"),
                    total_gross=Decimal("123.00"),
                ),
                Invoice(
                    id=invoice_sales_id,
                    tenant_id=tenant_id,
                    invoice_number="FV/S/01",
                    issue_date=date(2026, 3, 2),
                    seller_nip=test_nip,
                    buyer_nip="2222222222",
                    invoice_role="sales",
                    total_net=Decimal("200.00"),
                    total_vat=Decimal("46.00"),
                    total_gross=Decimal("246.00"),
                ),
                InvoiceLine(
                    tenant_id=tenant_id,
                    invoice_id=invoice_cost_id,
                    line_number=1,
                    product_name="Hosting",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                    line_net_value=Decimal("100.00"),
                    ai_category_main="IT",
                ),
                InvoiceLine(
                    tenant_id=tenant_id,
                    invoice_id=invoice_sales_id,
                    line_number=1,
                    product_name="Konsulting",
                    quantity=Decimal("1"),
                    unit_price=Decimal("200.00"),
                    line_net_value=Decimal("200.00"),
                    ai_category_main="IT",
                ),
            ]
        )
        await session.commit()

    token = create_access_token(user_id, tenant_id, "api-test@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        yield client, tenant_id

    async with async_session_factory() as session:
        await session.begin()
        await set_tenant_context(session, tenant_id)
        await session.execute(
            InvoiceLine.__table__.delete().where(InvoiceLine.tenant_id == tenant_id)
        )
        await session.execute(
            Invoice.__table__.delete().where(Invoice.tenant_id == tenant_id)
        )
        await session.execute(
            TenantCategory.__table__.delete().where(TenantCategory.tenant_id == tenant_id)
        )
        await session.execute(Tenant.__table__.delete().where(Tenant.id == tenant_id))
        await session.commit()
