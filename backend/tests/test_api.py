"""Testy warstwy API (HTTP + JWT + RLS)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_stats_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stats/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_api_endpoints(api_tenant_session):
    client, _tenant_id = api_tenant_session

    summary = await client.get("/api/v1/stats/summary", params={"role": "cost"})
    assert summary.status_code == 200
    assert summary.json()["total_net"] == "100.00"

    dashboard = await client.get(
        "/api/v1/stats/dashboard",
        params={"role": "cost", "date_from": "2026-03-01", "date_to": "2026-03-31"},
    )
    assert dashboard.status_code == 200
    dashboard_body = dashboard.json()
    assert "summary" in dashboard_body
    assert "cashflow" in dashboard_body

    cashflow = await client.get(
        "/api/v1/stats/cashflow",
        params={"date_from": "2026-03-01", "date_to": "2026-03-31"},
    )
    assert cashflow.status_code == 200
    cashflow_body = cashflow.json()
    assert cashflow_body["total_sales"] == "200.00"
    assert cashflow_body["total_costs"] == "100.00"

    invoices = await client.get(
        "/api/v1/invoices",
        params={"role": "cost", "category": "IT"},
    )
    assert invoices.status_code == 200
    items = invoices.json()
    assert len(items) == 1
    assert items[0]["invoice_number"] == "FV/C/01"


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "database" in body
    assert "ollama" in body
