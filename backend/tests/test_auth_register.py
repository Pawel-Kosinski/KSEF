"""Testy rejestracji multi-user (firma vs zaproszenie)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database.models import Tenant, User
from app.database.session import async_session_factory
from app.main import app


@pytest.mark.asyncio
async def test_register_new_company_creates_admin():
    transport = ASGITransport(app=app)
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    nip = str(uuid.uuid4().int % 9_000_000_000 + 1_000_000_000)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepass123",
                "company_name": "Test Sp. z o.o.",
                "nip": nip,
                "industry": "Usługi IT i software house",
            },
        )

    assert response.status_code == 201, response.text
    assert "access_token" in response.json()

    async with async_session_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one()
        tenant = await session.get(Tenant, user.tenant_id)
        assert user.role == "admin"
        assert tenant is not None
        assert tenant.invite_token
        assert len(tenant.invite_token) == 36

    async with async_session_factory() as session:
        await session.execute(User.__table__.delete().where(User.email == email))
        await session.execute(Tenant.__table__.delete().where(Tenant.nip == nip))
        await session.commit()


@pytest.mark.asyncio
async def test_register_with_invite_joins_existing_tenant():
    transport = ASGITransport(app=app)
    admin_email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    member_email = f"member-{uuid.uuid4().hex[:8]}@example.com"
    nip = str(uuid.uuid4().int % 9_000_000_000 + 1_000_000_000)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": admin_email,
                "password": "securepass123",
                "company_name": "Zespół Test",
                "nip": nip,
                "industry": "Konsulting biznesowy dla MŚP",
            },
        )
        assert create_res.status_code == 201

        async with async_session_factory() as session:
            admin = (
                await session.execute(select(User).where(User.email == admin_email))
            ).scalar_one()
            tenant = await session.get(Tenant, admin.tenant_id)
            invite_token = tenant.invite_token

        join_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": member_email,
                "password": "securepass123",
                "invite_token": invite_token,
            },
        )
        assert join_res.status_code == 201, join_res.text

        invalid_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"bad-{uuid.uuid4().hex[:8]}@example.com",
                "password": "securepass123",
                "invite_token": str(uuid.uuid4()),
            },
        )
        assert invalid_res.status_code == 400

    async with async_session_factory() as session:
        member = (
            await session.execute(select(User).where(User.email == member_email))
        ).scalar_one()
        admin = (
            await session.execute(select(User).where(User.email == admin_email))
        ).scalar_one()
        assert member.role == "user"
        assert member.tenant_id == admin.tenant_id

    async with async_session_factory() as session:
        tenant_id = (
            await session.execute(select(Tenant.id).where(Tenant.nip == nip))
        ).scalar_one()
        await session.execute(User.__table__.delete().where(User.tenant_id == tenant_id))
        await session.execute(Tenant.__table__.delete().where(Tenant.id == tenant_id))
        await session.commit()
