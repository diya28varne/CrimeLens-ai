"""Authentication HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import UnauthorizedError

from app.core.security import ACCESS_COOKIE, REFRESH_COOKIE, decode_access_token
from app.core.settings import Settings, get_settings
from app.infra.db.session import get_db_session
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import (
    LoginData,
    LoginRequest,
    LoginResponse,
    MeData,
    MeResponse,
    Jurisdictions,
    RefreshRequest,
    UserPublic,
)
from app.modules.identity.service import AuthService, MePayload

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(IdentityRepository(session), settings)


def _set_auth_cookies(response: Response, settings: Settings, access: str, refresh: str) -> None:
    common: dict = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
    }
    if settings.cookie_domain:
        common["domain"] = settings.cookie_domain
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=settings.jwt_access_ttl_minutes * 60,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=settings.jwt_refresh_ttl_days * 24 * 3600,
        **common,
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    kwargs: dict = {"path": "/"}
    if settings.cookie_domain:
        kwargs["domain"] = settings.cookie_domain
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, **kwargs)


def _to_user_public(me: MePayload) -> UserPublic:
    return UserPublic(
        id=me.user_id,
        email=me.email,
        full_name=me.full_name,
        status=me.status,  # type: ignore[arg-type]
    )


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return user_agent, ip


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    user_agent, ip = _client_meta(request)
    me, tokens = await service.login(
        email=str(body.email),
        password=body.password,
        user_agent=user_agent,
        ip_inet=ip,
    )
    if body.client == "browser":
        _set_auth_cookies(response, settings, tokens.access_token, tokens.refresh_token)
    # Always return the bearer token so the SPA works across localhost ↔ 127.0.0.1
    # (httpOnly cookies alone are not sent on cross-site fetches between those hosts).
    access_out = tokens.access_token

    return LoginResponse(
        data=LoginData(
            user=_to_user_public(me),
            access_token=access_out,
            expires_at=tokens.expires_at,
            permissions=list(me.permissions),
        )
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    refresh_token = body.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise UnauthorizedError("Refresh token required", details={"code": "SESSION_REVOKED"})
    user_agent, ip = _client_meta(request)
    me, tokens = await service.refresh(
        refresh_token=refresh_token,
        user_agent=user_agent,
        ip_inet=ip,
    )
    _set_auth_cookies(response, settings, tokens.access_token, tokens.refresh_token)
    return LoginResponse(
        data=LoginData(
            user=_to_user_public(me),
            access_token=tokens.access_token,
            expires_at=tokens.expires_at,
            permissions=list(me.permissions),
        )
    )


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    await service.logout(refresh_token)
    _clear_auth_cookies(response, settings)
    response.status_code = 204
    return response


async def get_current_auth_context(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext:
    token = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise UnauthorizedError("Authentication required")

    try:
        payload = decode_access_token(settings, token)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid access token type")

    user_id = UUID(str(payload["sub"]))
    service = AuthService(IdentityRepository(session), settings)
    user = await IdentityRepository(session).get_user_by_id(user_id)
    if user is None:
        raise UnauthorizedError("Authentication required")
    request_id = getattr(request.state, "request_id", None)
    return service.to_auth_context(user, request_id=request_id)


@router.get("/me", response_model=MeResponse)
async def me(
    ctx: Annotated[AuthContext, Depends(get_current_auth_context)],
    service: Annotated[AuthService, Depends(_auth_service)],
) -> MeResponse:
    payload = await service.me(ctx.user_id)
    return MeResponse(
        data=MeData(
            user=_to_user_public(payload),
            roles=list(payload.roles),
            permissions=list(payload.permissions),
            jurisdictions=Jurisdictions(
                district_ids=list(payload.district_ids),
                station_ids=list(payload.station_ids),
            ),
        )
    )
