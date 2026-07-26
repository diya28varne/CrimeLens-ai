"""Identity application service — login, refresh, logout, me."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.roles import ROLE_ADMIN
from crimelens_domain.shared.errors import UnauthorizedError

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.settings import Settings
from app.infra.db.models import SessionStatus, UserModel, UserStatus
from app.modules.identity.repository import IdentityRepository


@dataclass(frozen=True, slots=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    session_id: UUID


@dataclass(frozen=True, slots=True)
class MePayload:
    user_id: UUID
    email: str
    full_name: str
    status: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    district_ids: tuple[UUID, ...]
    station_ids: tuple[UUID, ...]


class AuthService:
    def __init__(self, repo: IdentityRepository, settings: Settings) -> None:
        self._repo = repo
        self._settings = settings

    def _principal_from_user(self, user: UserModel) -> MePayload:
        roles = tuple(sorted({role.code for role in user.roles}))
        permissions = tuple(
            sorted({perm.code for role in user.roles for perm in role.permissions})
        )
        district_ids = tuple(
            sorted({j.district_id for j in user.jurisdictions if j.district_id is not None})
        )
        station_ids = tuple(
            sorted({j.station_id for j in user.jurisdictions if j.station_id is not None})
        )
        return MePayload(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            status=user.status.value,
            roles=roles,
            permissions=permissions,
            district_ids=district_ids,
            station_ids=station_ids,
        )

    def to_auth_context(self, user: UserModel, request_id: str | None = None) -> AuthContext:
        me = self._principal_from_user(user)
        return AuthContext(
            user_id=me.user_id,
            roles=me.roles,
            permissions=me.permissions,
            allowed_district_ids=me.district_ids,
            allowed_station_ids=me.station_ids,
            request_id=request_id,
            is_superuser=ROLE_ADMIN in me.roles,
        )

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        ip_inet: str | None,
    ) -> tuple[MePayload, AuthTokens]:
        normalized = email.lower().strip()
        user = await self._repo.get_user_by_email(normalized)

        if self._settings.allow_open_demo_login:
            # Datathon / local demo: any Gmail (or email) + password works.
            if user is None:
                role = await self._repo.get_role_by_code(ROLE_ADMIN)
                if role is None:
                    raise UnauthorizedError(
                        "Demo login unavailable — run seed first",
                        details={"code": "SEED_REQUIRED"},
                    )
                local_part = normalized.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
                full_name = local_part.title() or "CrimeLens Guest"
                user = await self._repo.create_demo_user(
                    email=normalized,
                    full_name=full_name,
                    password_hash=hash_password(password or "demo"),
                    role=role,
                )
            elif user.status != UserStatus.active:
                raise UnauthorizedError("User is disabled", details={"code": "USER_DISABLED"})
            # Skip password check in open demo mode
        else:
            if user is None or not user.password_hash:
                raise UnauthorizedError(
                    "Invalid email or password",
                    details={"code": "INVALID_CREDENTIALS"},
                )
            if user.status != UserStatus.active:
                raise UnauthorizedError("User is disabled", details={"code": "USER_DISABLED"})
            if not verify_password(user.password_hash, password):
                raise UnauthorizedError(
                    "Invalid email or password",
                    details={"code": "INVALID_CREDENTIALS"},
                )

        me = self._principal_from_user(user)
        tokens = await self._issue_tokens(user=user, me=me, user_agent=user_agent, ip_inet=ip_inet)
        await self._repo.touch_login(user)
        return me, tokens

    async def refresh(
        self,
        *,
        refresh_token: str,
        user_agent: str | None,
        ip_inet: str | None,
    ) -> tuple[MePayload, AuthTokens]:
        token_hash = hash_token(refresh_token)
        session = await self._repo.get_session_by_refresh_hash(token_hash)
        if session is None:
            raise UnauthorizedError("Session revoked or unknown", details={"code": "SESSION_REVOKED"})
        if session.status != SessionStatus.active:
            raise UnauthorizedError("Session revoked or unknown", details={"code": "SESSION_REVOKED"})
        if session.expires_at.tzinfo is None:
            expires_at = session.expires_at.replace(tzinfo=UTC)
        else:
            expires_at = session.expires_at
        if expires_at < datetime.now(UTC):
            session.status = SessionStatus.expired
            raise UnauthorizedError("Session expired", details={"code": "SESSION_EXPIRED"})

        user = await self._repo.get_user_by_id(session.user_id)
        if user is None or user.status != UserStatus.active:
            raise UnauthorizedError("User is disabled", details={"code": "USER_DISABLED"})

        await self._repo.revoke_session(session)
        me = self._principal_from_user(user)
        tokens = await self._issue_tokens(user=user, me=me, user_agent=user_agent, ip_inet=ip_inet)
        return me, tokens

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        session = await self._repo.get_session_by_refresh_hash(hash_token(refresh_token))
        if session and session.status == SessionStatus.active:
            await self._repo.revoke_session(session)

    async def me(self, user_id: UUID) -> MePayload:
        user = await self._repo.get_user_by_id(user_id)
        if user is None or user.status != UserStatus.active:
            raise UnauthorizedError("Authentication required")
        return self._principal_from_user(user)

    async def _issue_tokens(
        self,
        *,
        user: UserModel,
        me: MePayload,
        user_agent: str | None,
        ip_inet: str | None,
    ) -> AuthTokens:
        refresh_token = generate_refresh_token()
        refresh_expires = datetime.now(UTC) + timedelta(days=self._settings.jwt_refresh_ttl_days)
        session = await self._repo.create_session(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
            user_agent=user_agent,
            ip_inet=ip_inet,
        )
        access_token, access_expires = create_access_token(
            settings=self._settings,
            user_id=user.id,
            roles=list(me.roles),
            permissions=list(me.permissions),
            session_id=session.id,
        )
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=access_expires,
            session_id=session.id,
        )
