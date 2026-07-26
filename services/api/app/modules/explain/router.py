"""Explainable AI Decision Engine HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import PREDICTION_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.explain.schemas import (
    AuditDetailResponse,
    AuditListResponse,
    DecisionCardResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from app.modules.explain.service import ExplainService

router = APIRouter(prefix="/explain", tags=["explain"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ExplainService:
    return ExplainService(session)


@router.get("/predictions/{value_id}", response_model=DecisionCardResponse)
async def decision_card(
    value_id: UUID,
    service: Annotated[ExplainService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
) -> DecisionCardResponse:
    return DecisionCardResponse(data=await service.decision_card(ctx, value_id))


@router.post("/predictions/{value_id}/what-if", response_model=WhatIfResponse)
async def what_if(
    value_id: UUID,
    body: WhatIfRequest,
    service: Annotated[ExplainService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
) -> WhatIfResponse:
    return WhatIfResponse(data=await service.what_if(ctx, value_id, body))


@router.get("/audit", response_model=AuditListResponse)
async def audit_list(
    service: Annotated[ExplainService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
    limit: int = Query(default=20, ge=1, le=50),
) -> AuditListResponse:
    _ = ctx
    return AuditListResponse(data=service.list_audit(limit=limit))


@router.get("/audit/{audit_id}", response_model=AuditDetailResponse)
async def audit_detail(
    audit_id: str,
    service: Annotated[ExplainService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
) -> AuditDetailResponse:
    _ = ctx
    record, card = service.get_audit(audit_id)
    return AuditDetailResponse(data=record, card=card)
