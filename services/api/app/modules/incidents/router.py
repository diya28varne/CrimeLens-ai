"""Incident HTTP routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import INCIDENT_INGEST, INCIDENT_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.incidents.repository import IncidentRepository
from app.modules.incidents.schemas import (
    IncidentDetailResponse,
    IncidentIngestRequest,
    IncidentIngestResponse,
    IncidentListResponse,
    IngestBatchResponse,
    OffenseTypeListResponse,
)
from app.modules.incidents.service import IncidentService

router = APIRouter(tags=["incidents"])


def _service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IncidentService:
    return IncidentService(IncidentRepository(session))


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    service: Annotated[IncidentService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
    district_id: UUID | None = None,
    station_id: UUID | None = None,
    offense_type_id: UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    occurred_from: datetime | None = Query(default=None, alias="from"),
    occurred_to: datetime | None = Query(default=None, alias="to"),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
) -> IncidentListResponse:
    data, page = await service.list_incidents(
        ctx,
        district_id=district_id,
        station_id=station_id,
        offense_type_id=offense_type_id,
        status=status,
        severity=severity,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        q=q,
        limit=limit,
        cursor=cursor,
    )
    return IncidentListResponse(data=data, page=page)


@router.get("/offense-types", response_model=OffenseTypeListResponse)
async def list_offense_types(
    service: Annotated[IncidentService, Depends(_service)],
    _: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
) -> OffenseTypeListResponse:
    return OffenseTypeListResponse(data=await service.list_offense_types())


@router.post("/incidents/ingest", response_model=IncidentIngestResponse)
async def ingest_incidents(
    body: IncidentIngestRequest,
    service: Annotated[IncidentService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_INGEST))],
) -> IncidentIngestResponse:
    return IncidentIngestResponse(data=await service.ingest(ctx, body))


@router.get("/incidents/ingest/batches/{batch_id}", response_model=IngestBatchResponse)
async def get_ingest_batch(
    batch_id: UUID,
    service: Annotated[IncidentService, Depends(_service)],
    _: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
) -> IngestBatchResponse:
    return IngestBatchResponse(data=await service.get_batch(batch_id))


@router.get("/incidents/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: UUID,
    service: Annotated[IncidentService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(INCIDENT_READ))],
) -> IncidentDetailResponse:
    return IncidentDetailResponse(data=await service.get_incident(ctx, incident_id))
