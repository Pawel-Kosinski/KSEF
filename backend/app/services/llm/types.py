"""Typy domenowe warstwy LLM (wiadomości, narzędzia, zdarzenia strumienia)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TextContentBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ToolUseContentBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResultContentBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str


ContentBlock = TextContentBlock | ToolUseContentBlock | ToolResultContentBlock


class LLMMessage(BaseModel):
    """Wiadomość w historii konwersacji przekazywana do modelu."""

    role: Literal["user", "assistant", "system"]
    content: str | list[ContentBlock]


class ToolCall(BaseModel):
    """Żądanie wywołania narzędzia zwrócone przez model."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Definicja narzędzia eksponowana modelowi (JSON Schema)."""

    name: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=1024)
    input_schema: dict[str, Any]

    def to_anthropic_tool(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def to_bedrock_tool_spec(self) -> dict[str, Any]:
        """Specyfikacja narzędzia dla AWS Bedrock Converse API."""
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {"json": self.input_schema},
            }
        }


class LLMStreamEventType:
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"


class LLMStreamEvent(BaseModel):
    """Zdarzenie strumienia z adaptera LLM."""

    type: Literal["text_delta", "tool_call", "message_complete", "error"]
    text: str | None = None
    tool_call: ToolCall | None = None
    assistant_message: LLMMessage | None = None
    error: str | None = None
