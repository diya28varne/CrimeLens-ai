"""Organization HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import INCIDENT_READ

from app.core.authz import require_permission
from app.infra.db.models import DistrictModel, PoliceStationModel
from app.infra.db.session import get_db_session
from app.modules.org.schemas import (
    DistrictListResponse,
    DistrictOut,
    StationListResponse,
    StationOut,
)

router = APIRouter(prefix="/org", tags=["org"])


@router.get("/districts", response_model=DistrictListResponse)
async def list_districts(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    q: str | None = Query(default=None),
    is_active: bool = Query(default=True),
) -> DistrictListResponse:
    stmt = select(DistrictModel).where(DistrictModel.is_active.is_(is_active))
    if not ctx.is_superuser:
        if not ctx.allowed_district_ids:
            return DistrictListResponse(data=[])
        stmt = stmt.where(DistrictModel.id.in_(ctx.allowed_district_ids))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (DistrictModel.name.ilike(like)) | (DistrictModel.code.ilike(like))
        )
    stmt = stmt.order_by(DistrictModel.code)
    rows = list((await session.scalars(stmt)).all())
    return DistrictListResponse(
        data=[
            DistrictOut(
                id=r.id,
                code=r.code,
                name=r.name,
                state_code=r.state_code,
                is_active=r.is_active,
            )
            for r in rows
        ]
    )


@router.get("/stations", response_model=StationListResponse)
async def list_stations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    district_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    is_active: bool = Query(default=True),
) -> StationListResponse:
    stmt = select(PoliceStationModel).where(PoliceStationModel.is_active.is_(is_active))
    if district_id is not None:
        if not ctx.is_superuser and district_id not in ctx.allowed_district_ids:
            return StationListResponse(data=[])
        stmt = stmt.where(PoliceStationModel.district_id == district_id)
    elif not ctx.is_superuser:
        if not ctx.allowed_district_ids and not ctx.allowed_station_ids:
            return StationListResponse(data=[])
        if ctx.allowed_station_ids:
            stmt = stmt.where(PoliceStationModel.id.in_(ctx.allowed_station_ids))
        else:
            stmt = stmt.where(PoliceStationModel.district_id.in_(ctx.allowed_district_ids))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (PoliceStationModel.name.ilike(like)) | (PoliceStationModel.code.ilike(like))
        )
    stmt = stmt.order_by(PoliceStationModel.code)
    rows = list((await session.scalars(stmt)).all())
    return StationListResponse(
        data=[
            StationOut(
                id=r.id,
                district_id=r.district_id,
                code=r.code,
                name=r.name,
                is_active=r.is_active,
            )
            for r in rows
        ]
    )
