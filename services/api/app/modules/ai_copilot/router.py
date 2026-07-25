"""AI copilot HTTP routes."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import AI_CHAT

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.ai_copilot.schemas import (
    AiChatRequest,
    AiChatSyncResponse,
    ConversationDetailResponse,
    ConversationsResponse,
)
from app.modules.ai_copilot.service import AiCopilotService

router = APIRouter(prefix="/ai", tags=["ai"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AiCopilotService:
    return AiCopilotService(session)


@router.get("/conversations", response_model=ConversationsResponse)
async def list_conversations(
    service: Annotated[AiCopilotService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(AI_CHAT))],
) -> ConversationsResponse:
    return ConversationsResponse(data=await service.list_conversations(ctx))


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    service: Annotated[AiCopilotService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(AI_CHAT))],
) -> ConversationDetailResponse:
    return ConversationDetailResponse(data=await service.get_conversation(ctx, conversation_id))


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    service: Annotated[AiCopilotService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(AI_CHAT))],
) -> None:
    await service.delete_conversation(ctx, conversation_id)


@router.post("/chat/sync", response_model=AiChatSyncResponse)
async def chat_sync(
    body: AiChatRequest,
    service: Annotated[AiCopilotService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(AI_CHAT))],
) -> AiChatSyncResponse:
    data = await service.chat_sync(
        ctx,
        message=body.message,
        conversation_id=body.conversation_id,
        district_id=body.district_id,
    )
    return AiChatSyncResponse(data=data)


@router.post("/chat")
async def chat_sse(
    body: AiChatRequest,
    service: Annotated[AiCopilotService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(AI_CHAT))],
) -> StreamingResponse:
    data = await service.chat_sync(
        ctx,
        message=body.message,
        conversation_id=body.conversation_id,
        district_id=body.district_id,
    )

    async def event_stream():
        yield _sse("conversation", {"conversation_id": str(data.conversation_id)})
        for t in data.tool_traces:
            yield _sse("tool_start", {"tool_name": t.tool_name})
            yield _sse(
                "tool_end",
                {"tool_name": t.tool_name, "status": t.status},
            )
        # stream tokens in chunks for UX
        chunk_size = 24
        for i in range(0, len(data.content), chunk_size):
            yield _sse("token", {"text": data.content[i : i + chunk_size]})
            await asyncio.sleep(0.01)
        for c in data.citations:
            yield _sse("citation", c.model_dump())
        yield _sse(
            "done",
            {"message_id": str(data.message_id), "finish_reason": "stop"},
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
