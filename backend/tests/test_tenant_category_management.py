"""Testy CRUD kategorii tenanta."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Invoice, InvoiceLine, Tenant, TenantCategory
from app.services.tenant_category_management import (
    CategoryDuplicateError,
    CategoryInUseError,
    CategoryNotFoundError,
    TenantCategoryManagementService,
    seed_tenant_categories,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


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
async def test_seed_and_list_categories(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1234567890"))
    await db_session.commit()

    await seed_tenant_categories(db_session, tenant_id, ["Koszt A", "Koszt B"])
    service = TenantCategoryManagementService(db_session, tenant_id)
    items = await service.list_categories()
    assert len(items) == 2
    assert items[0]["name"] == "Koszt A"


@pytest.mark.asyncio
async def test_create_duplicate_category_raises(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1234567890"))
    await seed_tenant_categories(db_session, tenant_id, ["Koszt A"])
    await db_session.commit()

    service = TenantCategoryManagementService(db_session, tenant_id)
    with pytest.raises(CategoryDuplicateError):
        await service.create_category("koszt a")


@pytest.mark.asyncio
async def test_delete_category_in_use_raises(db_session):
    tenant_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1234567890"))
    await seed_tenant_categories(db_session, tenant_id, ["Koszt A"])
    category = (
        await db_session.execute(
            select(TenantCategory).where(TenantCategory.tenant_id == tenant_id)
        )
    ).scalar_one()
    category_id = category.id

    db_session.add(
        Invoice(
            id=invoice_id,
            tenant_id=tenant_id,
            invoice_number="FV/1",
            issue_date=date(2025, 1, 1),
            currency_code="PLN",
            seller_nip="1111111111",
            buyer_nip="2222222222",
            primary_category_main="Koszt A",
        )
    )
    db_session.add(
        InvoiceLine(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            line_number=1,
            product_name="Test",
            quantity=Decimal("1"),
            unit_price=Decimal("100"),
            line_net_value=Decimal("100"),
            ai_category_main="Koszt A",
        )
    )
    await db_session.commit()

    service = TenantCategoryManagementService(db_session, tenant_id)
    with pytest.raises(CategoryInUseError):
        await service.delete_category(category_id)


@pytest.mark.asyncio
async def test_update_category_renames_references(db_session):
    tenant_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1234567890"))
    await seed_tenant_categories(db_session, tenant_id, ["Stara nazwa"])
    row = (
        await db_session.execute(
            select(TenantCategory).where(TenantCategory.tenant_id == tenant_id)
        )
    ).scalar_one()

    db_session.add(
        Invoice(
            id=invoice_id,
            tenant_id=tenant_id,
            invoice_number="FV/1",
            issue_date=date(2025, 1, 1),
            currency_code="PLN",
            seller_nip="1111111111",
            buyer_nip="2222222222",
            primary_category_main="Stara nazwa",
        )
    )
    await db_session.commit()

    service = TenantCategoryManagementService(db_session, tenant_id)
    updated = await service.update_category(row.id, "Nowa nazwa")
    assert updated["name"] == "Nowa nazwa"

    invoice = await db_session.get(Invoice, invoice_id)
    assert invoice.primary_category_main == "Nowa nazwa"


@pytest.mark.asyncio
async def test_delete_unused_category(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Test", nip="1234567890"))
    await seed_tenant_categories(db_session, tenant_id, ["Do usunięcia"])
    row = (
        await db_session.execute(
            select(TenantCategory).where(TenantCategory.tenant_id == tenant_id)
        )
    ).scalar_one()
    await db_session.commit()

    service = TenantCategoryManagementService(db_session, tenant_id)
    await service.delete_category(row.id)
    items = await service.list_categories()
    assert items == []
