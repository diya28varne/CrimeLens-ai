"""Admin overview — users, roles, feature registry."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext

from app.infra.db.models import PermissionModel, RoleModel, RolePermissionModel, UserModel, UserRoleModel
from app.modules.admin.schemas import AdminOverviewData, AdminRoleOut, AdminUserOut

FEATURE_FLAGS = [
    {"id": "simulation", "label": "Digital Twin Simulator", "route": "/simulation", "status": "live"},
    {"id": "advisor", "label": "Strategic Intelligence Advisor", "route": "/advisor", "status": "live"},
    {"id": "story", "label": "Crime Story Playback", "route": "/story", "status": "live"},
    {"id": "explain", "label": "Explainable AI Decision Engine", "route": "/explain", "status": "live"},
    {"id": "reports", "label": "Executive Intelligence Reports", "route": "/reports", "status": "live"},
    {"id": "map", "label": "Crime Map", "route": "/map", "status": "live"},
    {"id": "prediction", "label": "Prediction + SHAP", "route": "/prediction", "status": "live"},
    {"id": "network", "label": "Network / Repeat offenders", "route": "/network", "status": "live"},
]


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def overview(self, ctx: AuthContext, *, api_version: str) -> AdminOverviewData:
        _ = ctx
        users = (
            await self._session.execute(select(UserModel).order_by(UserModel.email))
        ).scalars().all()

        user_rows: list[AdminUserOut] = []
        for u in users:
            links = (
                await self._session.execute(
                    select(RoleModel.code)
                    .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
                    .where(UserRoleModel.user_id == u.id)
                )
            ).all()
            role_codes = [r[0] for r in links]
            user_rows.append(
                AdminUserOut(
                    id=u.id,
                    email=u.email,
                    full_name=u.full_name,
                    status=u.status.value if hasattr(u.status, "value") else str(u.status),
                    roles=role_codes,
                )
            )

        roles = (await self._session.execute(select(RoleModel).order_by(RoleModel.code))).scalars().all()
        role_rows: list[AdminRoleOut] = []
        for role in roles:
            cnt = await self._session.scalar(
                select(func.count())
                .select_from(RolePermissionModel)
                .where(RolePermissionModel.role_id == role.id)
            )
            role_rows.append(
                AdminRoleOut(code=role.code, name=role.name, permission_count=int(cnt or 0))
            )

        perms = (
            await self._session.execute(select(PermissionModel.code).order_by(PermissionModel.code))
        ).scalars().all()

        return AdminOverviewData(
            api_version=api_version,
            users=user_rows,
            roles=role_rows,
            permission_codes=list(perms),
            feature_flags=FEATURE_FLAGS,
        )
