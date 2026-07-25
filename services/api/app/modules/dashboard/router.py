"""Dashboard HTTP routes."""

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
from app.modules.dashboard.schemas import DashboardAlertsResponse, DashboardOverviewResponse
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> DashboardService:
    return DashboardService(session)


@router.get("/overview", response_model=DashboardOverviewResponse)
async def overview(
    service: Annotated[DashboardService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    district_id: UUID | None = None,
    station_id: UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
) -> DashboardOverviewResponse:
    data = await service.overview(
        ctx,
        district_id=district_id,
        station_id=station_id,
        from_=from_,
        to=to,
    )
    return DashboardOverviewResponse(data=data)


@router.get("/alerts", response_model=DashboardAlertsResponse)
async def alerts(
    service: Annotated[DashboardService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    district_id: UUID | None = None,
    station_id: UUID | None = None,
) -> DashboardAlertsResponse:
    return DashboardAlertsResponse(
        data=await service.alerts(ctx, district_id=district_id, station_id=station_id)
    )
