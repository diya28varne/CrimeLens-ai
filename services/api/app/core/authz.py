"""Require a permission on the current AuthContext."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import ForbiddenError

from app.modules.identity.router import get_current_auth_context


def require_permission(code: str) -> Callable[..., AuthContext]:
    async def _dep(ctx: AuthContext = Depends(get_current_auth_context)) -> AuthContext:
        if not ctx.has_permission(code):
            raise ForbiddenError(
                f"Missing permission: {code}",
                details={"code": "FORBIDDEN", "permission": code},
            )
        return ctx

    return _dep
