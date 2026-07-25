"""Crime analytics HTTP routes (trends / breakdown)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import ANALYTICS_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.analytics.crime_schemas import BreakdownResponse, TrendResponse
from app.modules.analytics.crime_service import CrimeAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> CrimeAnalyticsService:
    return CrimeAnalyticsService(session)


@router.get("/trends", response_model=TrendResponse)
async def trends(
    service: Annotated[CrimeAnalyticsService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    district_id: UUID | None = None,
    station_id: UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    interval: str = Query(default="day"),
) -> TrendResponse:
    return TrendResponse(
        data=await service.trends(
            ctx,
            district_id=district_id,
            station_id=station_id,
            from_=from_,
            to=to,
            interval=interval,
        )
    )


@router.get("/breakdown", response_model=BreakdownResponse)
async def breakdown(
    service: Annotated[CrimeAnalyticsService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    district_id: UUID | None = None,
    station_id: UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    group_by: str = Query(default="offense"),
) -> BreakdownResponse:
    return BreakdownResponse(
        data=await service.breakdown(
            ctx,
            district_id=district_id,
            station_id=station_id,
            from_=from_,
            to=to,
            group_by=group_by,
        )
    )
