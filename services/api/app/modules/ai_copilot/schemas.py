"""AI copilot schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=4000)
    district_id: UUID | None = None
    station_id: UUID | None = None
    mode: str = "ask"


class Citation(BaseModel):
    type: str
    id: str
    label: str
    href: str | None = None


class ToolTraceSummary(BaseModel):
    tool_name: str
    status: str
    latency_ms: int | None = None


class AiChatSyncResponseData(BaseModel):
    conversation_id: UUID
    message_id: UUID
    content: str
    citations: list[Citation] = Field(default_factory=list)
    tool_traces: list[ToolTraceSummary] = Field(default_factory=list)


class AiChatSyncResponse(BaseModel):
    data: AiChatSyncResponseData


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    updated_at: datetime
    district_id: UUID | None = None


class ConversationsResponse(BaseModel):
    data: list[ConversationSummary]


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime


class ConversationDetail(BaseModel):
    conversation: ConversationSummary
    messages: list[MessageOut]


class ConversationDetailResponse(BaseModel):
    data: ConversationDetail
