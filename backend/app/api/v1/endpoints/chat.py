"""Endpoint Virtual CFO Chat (SSE + agent loop)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.schemas.chat import ChatMessageRequest
from app.services.llm.agent import ChatAgentService
from app.services.llm.factory import get_llm_service
from app.services.llm.tools import ToolExecutionContext, get_tool_registry

router = APIRouter(prefix="/chat", tags=["Virtual CFO Chat"])


def _chat_agent() -> ChatAgentService:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "claude" and not settings.anthropic_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat AI jest niedostępny – skonfiguruj ANTHROPIC_API_KEY",
        )

    if provider == "bedrock" and not settings.aws_default_region.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat AI jest niedostępny – skonfiguruj AWS_DEFAULT_REGION",
        )

    return ChatAgentService(llm=get_llm_service(), tools=get_tool_registry())


def _format_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/message")
async def chat_message(
    body: ChatMessageRequest,
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
    agent: ChatAgentService = Depends(_chat_agent),
) -> StreamingResponse:
    context = ToolExecutionContext(tenant_id=tenant.tenant_id, session=session)
    history = [message.model_dump() for message in body.messages]

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in agent.stream_chat(history, context):
                yield _format_sse(event)
                if event.get("type") in ("done", "error"):
                    break
        except Exception as exc:
            yield _format_sse({"type": "error", "content": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
