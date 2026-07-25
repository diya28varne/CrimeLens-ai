"""FastAPI dependency providers."""

from __future__ import annotations

from fastapi import Request

from app.core.settings import Settings, get_settings
from app.infra.db.session import get_db_session
from app.modules.identity.router import get_current_auth_context

__all__ = [
    "get_settings",
    "get_db_session",
    "get_current_auth_context",
    "settings_dep",
    "request_id_dep",
]


def settings_dep() -> Settings:
    return get_settings()


def request_id_dep(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")
