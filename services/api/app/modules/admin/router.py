"""Admin HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import ADMIN_USERS

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.admin.schemas import AdminOverviewResponse
from app.modules.admin.service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> AdminService:
    return AdminService(session)


@router.get("/overview", response_model=AdminOverviewResponse)
async def admin_overview(
    service: Annotated[AdminService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(ADMIN_USERS))],
) -> AdminOverviewResponse:
    return AdminOverviewResponse(data=await service.overview(ctx, api_version="0.11.0"))
