"""Identity authorization policies."""

from __future__ import annotations

from uuid import UUID

from crimelens_domain.identity.auth_context import AuthContext, PermissionCode
from crimelens_domain.shared.errors import ForbiddenError, UnauthorizedError


def require_authenticated(ctx: AuthContext | None) -> AuthContext:
    if ctx is None:
        raise UnauthorizedError("Authentication required")
    return ctx


def require_permission(ctx: AuthContext, code: PermissionCode) -> None:
    if not ctx.has_permission(code):
        raise ForbiddenError(
            f"Missing permission: {code}",
            details={"permission": code},
        )


def require_district_access(ctx: AuthContext, district_id: UUID) -> None:
    if not ctx.can_access_district(district_id):
        raise ForbiddenError(
            "Jurisdiction denied for district",
            details={"district_id": str(district_id)},
        )


def require_station_access(ctx: AuthContext, station_id: UUID) -> None:
    if not ctx.can_access_station(station_id):
        raise ForbiddenError(
            "Jurisdiction denied for station",
            details={"station_id": str(station_id)},
        )
