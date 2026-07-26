"""Digital Twin / Decision Simulation HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import PREDICTION_READ

from app.core.authz import require_permission
from app.infra.db.session import get_db_session
from app.modules.simulation.schemas import (
    ScenarioPresetOut,
    ScenariosResponse,
    SimulationRunRequest,
    SimulationRunResponse,
)
from app.modules.simulation.service import SimulationService

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> SimulationService:
    return SimulationService(session)


@router.get("/scenarios", response_model=ScenariosResponse)
async def list_scenarios(
    service: Annotated[SimulationService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
) -> ScenariosResponse:
    rows = await service.list_scenarios(ctx)
    return ScenariosResponse(data=[ScenarioPresetOut(**r) for r in rows])


@router.post("/runs", response_model=SimulationRunResponse)
async def create_run(
    body: SimulationRunRequest,
    service: Annotated[SimulationService, Depends(_service)],
    ctx: Annotated[AuthContext, Depends(require_permission(PREDICTION_READ))],
) -> SimulationRunResponse:
    return SimulationRunResponse(data=await service.run(ctx, body))
