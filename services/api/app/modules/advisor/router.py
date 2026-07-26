"""Strategic Intelligence Advisor HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import ANALYTICS_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.advisor.schemas import AdvisorBriefResponse, AdvisorHistoryResponse
from app.modules.advisor.service import AdvisorService

router = APIRouter(prefix="/advisor", tags=["advisor"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AdvisorService:
    return AdvisorService(session)


@router.get("/brief/current", response_model=AdvisorBriefResponse)
async def brief_current(
    service: Annotated[AdvisorService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
) -> AdvisorBriefResponse:
    return AdvisorBriefResponse(data=await service.current_brief(ctx))


@router.post("/brief/refresh", response_model=AdvisorBriefResponse)
async def brief_refresh(
    service: Annotated[AdvisorService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
) -> AdvisorBriefResponse:
    return AdvisorBriefResponse(data=await service.refresh(ctx))


@router.get("/brief/history", response_model=AdvisorHistoryResponse)
async def brief_history(
    service: Annotated[AdvisorService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    limit: int = Query(default=14, ge=1, le=30),
) -> AdvisorHistoryResponse:
    _ = ctx
    history = service.history(limit=limit)
    if not history:
        # Ensure current brief exists so timeline seeds
        brief = await service.current_brief(ctx)
        history = brief.timeline[:limit]
    return AdvisorHistoryResponse(data=history)
