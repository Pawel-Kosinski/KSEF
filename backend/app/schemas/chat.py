"""Schematy API Virtual CFO Chat."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=32_000)


class ChatMessageRequest(BaseModel):
    messages: list[ChatHistoryMessage] = Field(
        min_length=1,
        max_length=100,
        description="Historia konwersacji (ostatnia wiadomość od użytkownika)",
    )


class ChatStreamEvent(BaseModel):
    """Zdarzenie SSE wysyłane do klienta."""

    type: Literal["text", "tool_start", "tool_result", "done", "error"]
    content: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
