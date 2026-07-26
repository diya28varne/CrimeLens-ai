"""Executive intelligence report HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import ANALYTICS_READ
from crimelens_domain.shared.errors import NotFoundError

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.reports.schemas import (
    GenerateReportRequest,
    GenerateReportResponse,
    GetReportResponse,
    TemplatesResponse,
)
from app.modules.reports.service import ReportsService

router = APIRouter(prefix="/reports", tags=["reports"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> ReportsService:
    return ReportsService(session)


@router.get("/templates", response_model=TemplatesResponse)
async def list_templates(
    service: Annotated[ReportsService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
) -> TemplatesResponse:
    _ = ctx
    return TemplatesResponse(data=service.list_templates())


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    body: GenerateReportRequest,
    service: Annotated[ReportsService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
) -> GenerateReportResponse:
    return GenerateReportResponse(data=await service.generate(ctx, body))


@router.get("/{report_id}", response_model=GetReportResponse)
async def get_report(
    report_id: str,
    service: Annotated[ReportsService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ANALYTICS_READ))],
) -> GetReportResponse:
    _ = ctx
    report = service.get_cached(report_id)
    if report is None:
        raise NotFoundError("Report not found or expired", details={"code": "NOT_FOUND"})
    return GetReportResponse(data=report)
