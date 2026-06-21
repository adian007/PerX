"""Pydantic schemas for the Ask PerX chat endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatHistoryMessage(BaseModel):
    """Prior turn in the chat thread."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    """Body for POST /api/v1/chat."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=8)


class ChatAction(BaseModel):
    """UI action the client can render after a reply."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["link", "save_perk"]
    label: str = Field(max_length=120)
    href: str | None = None
    perk_id: str | None = None
    perk_name: str | None = None


class ChatResponseData(BaseModel):
    """Chat reply payload."""

    model_config = ConfigDict(strict=True)

    reply: str
    model: str
    source: str
    actions: list[ChatAction] = Field(default_factory=list)
