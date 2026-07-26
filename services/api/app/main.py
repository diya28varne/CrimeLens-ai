"""CrimeLens API composition root."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings
from app.middleware.request_id import RequestIdMiddleware
from app.modules.health.router import router as health_router
from app.modules.identity.router import router as identity_router
from app.modules.analytics.router import router as socio_analytics_router
from app.modules.analytics.crime_router import router as crime_analytics_router
from app.modules.org.router import router as org_router
from app.modules.incidents.router import router as incidents_router
from app.modules.spatial.router import router as spatial_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.predictions.router import router as predictions_router
from app.modules.network.router import router as network_router
from app.modules.simulation.router import router as simulation_router
from app.modules.advisor.router import router as advisor_router
from app.modules.story.router import router as story_router
from app.modules.explain.router import router as explain_router
from app.modules.reports.router import router as reports_router
from app.modules.admin.router import router as admin_router
from app.modules.ai_copilot.router import router as ai_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "api_starting",
        extra={"app_env": settings.app_env, "app_name": settings.app_name},
    )
    yield
    logger.info("api_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.12.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestIdMiddleware)
    register_exception_handlers(application)

    application.include_router(health_router, prefix="/api/v1")
    application.include_router(identity_router, prefix="/api/v1")
    application.include_router(org_router, prefix="/api/v1")
    application.include_router(incidents_router, prefix="/api/v1")
    application.include_router(spatial_router, prefix="/api/v1")
    application.include_router(dashboard_router, prefix="/api/v1")
    application.include_router(crime_analytics_router, prefix="/api/v1")
    application.include_router(socio_analytics_router, prefix="/api/v1")
    application.include_router(predictions_router, prefix="/api/v1")
    application.include_router(network_router, prefix="/api/v1")
    application.include_router(simulation_router, prefix="/api/v1")
    application.include_router(advisor_router, prefix="/api/v1")
    application.include_router(story_router, prefix="/api/v1")
    application.include_router(explain_router, prefix="/api/v1")
    application.include_router(reports_router, prefix="/api/v1")
    application.include_router(admin_router, prefix="/api/v1")
    application.include_router(ai_router, prefix="/api/v1")

    return application


app = create_app()
