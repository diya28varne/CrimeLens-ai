"""Spatial HTTP routes — GeoJSON incident layers."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import INCIDENT_READ
from crimelens_domain.shared.errors import ValidationAppError

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.incidents.repository import IncidentRepository
from app.modules.incidents.service import IncidentService

router = APIRouter(prefix="/spatial", tags=["spatial"])


def _service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IncidentService:
    return IncidentService(IncidentRepository(session))


@router.get("/incidents")
async def spatial_incidents(
    service: Annotated[IncidentService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    bbox: str | None = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    lon: float | None = None,
    lat: float | None = None,
    radius_m: float | None = Query(default=None, gt=0),
    occurred_from: datetime | None = Query(default=None, alias="from"),
    occurred_to: datetime | None = Query(default=None, alias="to"),
    offense_type_id: UUID | None = None,
    limit: int = Query(default=2000, ge=1, le=5000),
) -> JSONResponse:
    try:
        collection = await service.spatial_features(
            ctx,
            bbox=bbox,
            lon=lon,
            lat=lat,
            radius_m=radius_m,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            offense_type_id=offense_type_id,
            limit=limit,
        )
    except ValueError as exc:
        raise ValidationAppError(str(exc)) from exc
    return JSONResponse(content=collection, media_type="application/geo+json")


@router.get("/radius")
async def spatial_radius_json(
    service: Annotated[IncidentService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    lon: float = Query(...),
    lat: float = Query(...),
    radius_m: float = Query(..., gt=0),
    occurred_from: datetime | None = Query(default=None, alias="from"),
    occurred_to: datetime | None = Query(default=None, alias="to"),
    offense_type_id: UUID | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
) -> dict[str, Any]:
    collection = await service.spatial_features(
        ctx,
        bbox=None,
        lon=lon,
        lat=lat,
        radius_m=radius_m,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        offense_type_id=offense_type_id,
        limit=limit,
    )
    return {
        "data": {
            "count": len(collection["features"]),
            "features": collection["features"],
        }
    }
