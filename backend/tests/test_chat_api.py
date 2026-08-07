"""Testy endpointu chat (SSE)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import chat as chat_endpoint
from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.main import app
from app.services.llm.agent import ChatAgentService


class StubChatAgent(ChatAgentService):
    def __init__(self) -> None:
        pass

    async def stream_chat(
        self,
        history: list[dict[str, str]],
        context: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "text", "content": "Odpowiedź testowa"}
        yield {"type": "done"}


@pytest.fixture
def chat_client():
    tenant_id = uuid4()
    user_id = uuid4()

    async def override_tenant():
        return TenantContext(tenant_id=tenant_id, user_id=user_id, email="chat@test.com")

    async def override_session():
        from unittest.mock import AsyncMock

        session = AsyncMock()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    def override_agent():
        return StubChatAgent()

    app.dependency_overrides[get_current_tenant] = override_tenant
    app.dependency_overrides[get_rls_session] = override_session
    app.dependency_overrides[chat_endpoint._chat_agent] = override_agent

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_message_streams_sse(chat_client: AsyncClient):
    response = await chat_client.post(
        "/api/v1/chat/message",
        json={"messages": [{"role": "user", "content": "Jakie mam koszty?"}]},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = response.text
    assert '"type": "text"' in body
    assert "Odpowiedź testowa" in body
    assert '"type": "done"' in body
