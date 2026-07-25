"""Identity persistence repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infra.db.models import (
    AuthSessionModel,
    RoleModel,
    SessionStatus,
    UserModel,
)


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _user_options(self) -> tuple:
        return (
            selectinload(UserModel.roles).selectinload(RoleModel.permissions),
            selectinload(UserModel.jurisdictions),
        )

    async def get_user_by_email(self, email: str) -> UserModel | None:
        stmt = (
            select(UserModel)
            .where(UserModel.email == email.lower(), UserModel.deleted_at.is_(None))
            .options(*self._user_options())
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> UserModel | None:
        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id, UserModel.deleted_at.is_(None))
            .options(*self._user_options())
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_session(
        self,
        *,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_inet: str | None,
    ) -> AuthSessionModel:
        session = AuthSessionModel(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            status=SessionStatus.active,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_inet=ip_inet,
        )
        self._session.add(session)
        await self._session.flush()
        return session

    async def get_session_by_refresh_hash(self, token_hash: str) -> AuthSessionModel | None:
        stmt = select(AuthSessionModel).where(AuthSessionModel.refresh_token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_session(self, session: AuthSessionModel) -> None:
        session.status = SessionStatus.revoked
        session.revoked_at = datetime.now(UTC)
        await self._session.flush()

    async def touch_login(self, user: UserModel) -> None:
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()
