"""Prediction HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import PREDICTION_READ

from app.core.authz import require_permission
from app.infra.db.models import PredictionMetric
from app.infra.db.session import get_db_session
from app.modules.predictions.schemas import (
    CurrentPredictionsResponse,
    ExplanationResponse,
    HotspotsCurrentResponse,
    ModelsResponse,
    RunsResponse,
)
from app.modules.predictions.service import PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> PredictionService:
    return PredictionService(session)


@router.get("/runs", response_model=RunsResponse)
async def list_runs(
    service: Annotated[PredictionService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
    is_current: bool | None = None,
) -> RunsResponse:
    return RunsResponse(data=await service.list_runs(ctx, is_current=is_current))


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    service: Annotated[PredictionService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
) -> ModelsResponse:
    return ModelsResponse(data=await service.list_models(ctx))


@router.get("/current", response_model=CurrentPredictionsResponse)
async def current_predictions(
    service: Annotated[PredictionService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
    metric: PredictionMetric = PredictionMetric.risk_score,
    district_id: UUID | None = None,
    station_id: UUID | None = None,
    top_n: int = Query(default=20, ge=1, le=100),
) -> CurrentPredictionsResponse:
    return CurrentPredictionsResponse(
        data=await service.current(
            ctx,
            metric=metric,
            district_id=district_id,
            station_id=station_id,
            top_n=top_n,
        )
    )


@router.get("/values/{value_id}/explanation", response_model=ExplanationResponse)
async def value_explanation(
    value_id: UUID,
    service: Annotated[PredictionService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
) -> ExplanationResponse:
    return ExplanationResponse(data=await service.explanation(ctx, value_id))


@router.get("/hotspots/current", response_model=HotspotsCurrentResponse)
async def hotspots_current(
    service: Annotated[PredictionService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
    district_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> HotspotsCurrentResponse:
    return HotspotsCurrentResponse(
        data=await service.hotspots_current(ctx, district_id=district_id, limit=limit)
    )
