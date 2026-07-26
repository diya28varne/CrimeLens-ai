"""Seed roles, permissions, demo district/station, and admin user."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity.permissions import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS
from crimelens_domain.identity.roles import ROLE_NAMES, ROLE_PERMISSIONS, ROLE_ADMIN

from app.core.security import hash_password
from app.infra.db.models import (
    DistrictModel,
    PermissionModel,
    PoliceStationModel,
    RoleModel,
    RolePermissionModel,
    UserJurisdictionModel,
    UserModel,
    UserRoleModel,
    UserStatus,
)
from app.infra.async_runtime import run_async
from app.infra.db.session import get_engine, get_session_factory


async def seed(session: AsyncSession) -> None:
    # Permissions
    perm_by_code: dict[str, PermissionModel] = {}
    for code in ALL_PERMISSIONS:
        existing = await session.scalar(select(PermissionModel).where(PermissionModel.code == code))
        if existing:
            perm_by_code[code] = existing
            continue
        row = PermissionModel(id=uuid.uuid4(), code=code, description=PERMISSION_DESCRIPTIONS.get(code))
        session.add(row)
        perm_by_code[code] = row
    await session.flush()

    # Roles + grants
    role_by_code: dict[str, RoleModel] = {}
    for code, name in ROLE_NAMES.items():
        existing = await session.scalar(select(RoleModel).where(RoleModel.code == code))
        if existing:
            role_by_code[code] = existing
        else:
            role = RoleModel(id=uuid.uuid4(), code=code, name=name, description=name)
            session.add(role)
            await session.flush()
            role_by_code[code] = role

        role = role_by_code[code]
        for perm_code in ROLE_PERMISSIONS[code]:
            exists = await session.scalar(
                select(RolePermissionModel).where(
                    RolePermissionModel.role_id == role.id,
                    RolePermissionModel.permission_id == perm_by_code[perm_code].id,
                )
            )
            if not exists:
                session.add(
                    RolePermissionModel(
                        role_id=role.id,
                        permission_id=perm_by_code[perm_code].id,
                    )
                )
    await session.flush()

    # Demo district / station
    district = await session.scalar(select(DistrictModel).where(DistrictModel.code == "BLR"))
    if not district:
        district = DistrictModel(id=uuid.uuid4(), code="BLR", name="Bengaluru City", state_code="KA")
        session.add(district)
        await session.flush()

    station = await session.scalar(
        select(PoliceStationModel).where(
            PoliceStationModel.district_id == district.id,
            PoliceStationModel.code == "BLR-CENTRAL",
        )
    )
    if not station:
        station = PoliceStationModel(
            id=uuid.uuid4(),
            district_id=district.id,
            code="BLR-CENTRAL",
            name="Bengaluru Central",
        )
        session.add(station)
        await session.flush()

    # Admin user
    admin_email = "admin@crimelens.local"
    admin = await session.scalar(select(UserModel).where(UserModel.email == admin_email))
    if not admin:
        admin = UserModel(
            id=uuid.uuid4(),
            email=admin_email,
            full_name="CrimeLens Admin",
            password_hash=hash_password("ChangeMe123!"),
            status=UserStatus.active,
        )
        session.add(admin)
        await session.flush()
        session.add(UserRoleModel(user_id=admin.id, role_id=role_by_code[ROLE_ADMIN].id))
        session.add(
            UserJurisdictionModel(
                id=uuid.uuid4(),
                user_id=admin.id,
                district_id=district.id,
                station_id=None,
            )
        )

    await session.commit()
    print("Seed complete.")
    print(f"  admin email: {admin_email}")
    print("  admin password: ChangeMe123!")
    print(f"  district: {district.code} / station: {station.code}")


async def main() -> None:
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    run_async(main())
