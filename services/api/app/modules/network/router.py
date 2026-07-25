"""Network HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import NETWORK_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.network.schemas import (
    NetworkGraphResponse,
    PersonDetailResponse,
    RepeatOffendersResponse,
)
from app.modules.network.service import NetworkService

router = APIRouter(prefix="/network", tags=["network"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> NetworkService:
    return NetworkService(session)


@router.get("/graph", response_model=NetworkGraphResponse)
async def graph(
    service: Annotated[NetworkService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(NETWORK_READ))],
    person_id: UUID | None = None,
    min_weight: float = Query(default=0.0, ge=0),
    limit_nodes: int = Query(default=50, ge=1, le=200),
) -> NetworkGraphResponse:
    return NetworkGraphResponse(
        data=await service.graph(
            ctx, person_id=person_id, min_weight=min_weight, limit_nodes=limit_nodes
        )
    )


@router.get("/persons/{person_id}", response_model=PersonDetailResponse)
async def person_detail(
    person_id: UUID,
    service: Annotated[NetworkService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(NETWORK_READ))],
) -> PersonDetailResponse:
    return PersonDetailResponse(data=await service.person(ctx, person_id))


@router.get("/repeat-offenders", response_model=RepeatOffendersResponse)
async def repeat_offenders(
    service: Annotated[NetworkService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(NETWORK_READ))],
    limit: int = Query(default=20, ge=1, le=100),
) -> RepeatOffendersResponse:
    return RepeatOffendersResponse(data=await service.repeat_offenders(ctx, limit=limit))
