"""Analytics HTTP routes — socio-economic correlation."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import ANALYTICS_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.analytics.repository import SocioEconomicRepository
from app.modules.analytics.schemas import (
    CorrelationListResponse,
    CorrelationResponse,
    CrimeMetricListResponse,
    IndicatorListResponse,
)
from app.modules.analytics.service import SocioEconomicService

router = APIRouter(prefix="/analytics/socio-economic", tags=["analytics", "socio-economic"])


def _service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SocioEconomicService:
    return SocioEconomicService(SocioEconomicRepository(session))


@router.get("/indicators", response_model=IndicatorListResponse)
async def list_indicators(
    service: Annotated[SocioEconomicService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    year: int | None = Query(default=None),
    district_id: UUID | None = Query(default=None),
    indicator_code: str | None = Query(default=None),
) -> IndicatorListResponse:
    rows = await service.list_indicators(
        ctx,
        year=year,
        district_id=district_id,
        indicator_code=indicator_code,
    )
    return IndicatorListResponse(data=rows)


@router.get("/crime-metrics", response_model=CrimeMetricListResponse)
async def list_crime_metrics(
    service: Annotated[SocioEconomicService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    year: int | None = Query(default=None),
    district_id: UUID | None = Query(default=None),
) -> CrimeMetricListResponse:
    rows = await service.list_crime_metrics(ctx, year=year, district_id=district_id)
    return CrimeMetricListResponse(data=rows)


@router.get("/correlation", response_model=CorrelationResponse)
async def correlation(
    service: Annotated[SocioEconomicService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    indicator_code: str = Query(...),
    year: int | None = Query(default=None),
    crime_metric: Literal["crime_rate_per_100k", "incident_count"] = Query(
        default="crime_rate_per_100k"
    ),
) -> CorrelationResponse:
    result = await service.correlate(
        ctx,
        year=year,
        indicator_code=indicator_code,
        crime_metric=crime_metric,
    )
    return CorrelationResponse(data=result)


@router.get("/correlations", response_model=CorrelationListResponse)
async def correlations(
    service: Annotated[SocioEconomicService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
    year: int | None = Query(default=None),
    crime_metric: Literal["crime_rate_per_100k", "incident_count"] = Query(
        default="crime_rate_per_100k"
    ),
) -> CorrelationListResponse:
    rows = await service.rank_correlations(ctx, year=year, crime_metric=crime_metric)
    return CorrelationListResponse(data=rows)
