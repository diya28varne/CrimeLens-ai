"""Crime Story Playback HTTP routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import INCIDENT_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.story.schemas import (
    DetectiveRequest,
    DetectiveResponse,
    JourneyResponse,
    StoryChaptersResponse,
    StoryEventsResponse,
    StoryFramesResponse,
    StoryRangeResponse,
)
from app.modules.story.service import StoryService

router = APIRouter(prefix="/story", tags=["story"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> StoryService:
    return StoryService(session)


@router.get("/range", response_model=StoryRangeResponse)
async def story_range(
    service: Annotated[StoryService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    offense_code: str | None = None,
    district_id: UUID | None = None,
) -> StoryRangeResponse:
    return StoryRangeResponse(
        data=await service.resolve_range(
            ctx, from_=from_, to=to, offense_code=offense_code, district_id=district_id
        )
    )


@router.get("/frames", response_model=StoryFramesResponse)
async def story_frames(
    service: Annotated[StoryService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    offense_code: str | None = None,
    district_id: UUID | None = None,
) -> StoryFramesResponse:
    return StoryFramesResponse(
        data=await service.frames(
            ctx, from_=from_, to=to, offense_code=offense_code, district_id=district_id
        )
    )


@router.get("/chapters", response_model=StoryChaptersResponse)
async def story_chapters(
    service: Annotated[StoryService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    offense_code: str | None = None,
    district_id: UUID | None = None,
) -> StoryChaptersResponse:
    return StoryChaptersResponse(
        data=await service.chapters(
            ctx, from_=from_, to=to, offense_code=offense_code, district_id=district_id
        )
    )


@router.get("/events", response_model=StoryEventsResponse)
async def story_events(
    service: Annotated[StoryService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
) -> StoryEventsResponse:
    _ = ctx
    return StoryEventsResponse(data=service.events(from_=from_, to=to))


@router.post("/detective", response_model=DetectiveResponse)
async def story_detective(
    body: DetectiveRequest,
    service: Annotated[StoryService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
) -> DetectiveResponse:
    return DetectiveResponse(data=await service.detective(ctx, body))


@router.get("/journey/{incident_id}", response_model=JourneyResponse)
async def story_journey(
    incident_id: UUID,
    service: Annotated[StoryService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
) -> JourneyResponse:
    return JourneyResponse(data=await service.journey(ctx, incident_id))
