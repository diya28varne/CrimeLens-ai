"""Health endpoints — liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.settings import get_settings
from app.infra.db.session import get_engine
from app.infra.redis.client import ping_redis

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    status: str = Field(examples=["ok"])


class ReadyStatus(BaseModel):
    status: str
    postgres: str
    redis: str


@router.get("/live", response_model=HealthStatus)
async def live() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/ready", response_model=ReadyStatus)
async def ready(response: Response) -> ReadyStatus:
    settings = get_settings()
    postgres_status = "ok"
    redis_status = "ok"

    try:
        engine = get_engine(settings.postgres_url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — readiness must never raise
        postgres_status = "error"

    try:
        await ping_redis(settings.redis_url)
    except Exception:  # noqa: BLE001
        redis_status = "error"

    overall = "ok" if postgres_status == "ok" and redis_status == "ok" else "degraded"
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyStatus(status=overall, postgres=postgres_status, redis=redis_status)
