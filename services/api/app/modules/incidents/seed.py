"""Seed offense taxonomy + sample Karnataka incidents (PostGIS points)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.geo import point_geography
from app.infra.db.models import (
    IncidentModel,
    IncidentSource,
    IncidentStatus,
    OffenseCategoryModel,
    OffenseTypeModel,
    PoliceStationModel,
    SeverityLevel,
)
from app.infra.db.session import get_engine, get_session_factory

OFFENSES: list[tuple[str, str, list[tuple[str, str, SeverityLevel]]]] = [
    (
        "PROPERTY",
        "Property crime",
        [
            ("THEFT", "Theft", SeverityLevel.medium),
            ("BURGLARY", "Burglary", SeverityLevel.high),
            ("ROBBERY", "Robbery", SeverityLevel.critical),
        ],
    ),
    (
        "VIOLENT",
        "Violent crime",
        [
            ("ASSAULT", "Assault", SeverityLevel.high),
            ("HOMICIDE", "Homicide", SeverityLevel.critical),
        ],
    ),
    (
        "CYBER",
        "Cyber crime",
        [
            ("CYBER_FRAUD", "Cyber fraud", SeverityLevel.medium),
        ],
    ),
]

# station_code, offense_code, lon, lat, days_ago, severity
SAMPLE_INCIDENTS: list[tuple[str, str, float, float, int, SeverityLevel]] = [
    ("BLR-CENTRAL", "THEFT", 77.5946, 12.9716, 2, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.5800, 12.9650, 5, SeverityLevel.high),
    ("BLR-CENTRAL", "CYBER_FRAUD", 77.6000, 12.9800, 1, SeverityLevel.medium),
    ("BLR-CENTRAL", "ASSAULT", 77.5900, 12.9600, 8, SeverityLevel.high),
    ("BLR-CENTRAL", "ROBBERY", 77.5850, 12.9750, 12, SeverityLevel.critical),
    ("BLR-CENTRAL", "THEFT", 77.6050, 12.9700, 3, SeverityLevel.low),
    ("BLR-CENTRAL", "THEFT", 77.5700, 12.9550, 15, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.6100, 12.9850, 20, SeverityLevel.high),
]


async def seed_incidents(session: AsyncSession) -> None:
    offense_by_code: dict[str, OffenseTypeModel] = {}
    for cat_code, cat_name, types in OFFENSES:
        category = await session.scalar(
            select(OffenseCategoryModel).where(OffenseCategoryModel.code == cat_code)
        )
        if not category:
            category = OffenseCategoryModel(id=uuid.uuid4(), code=cat_code, name=cat_name)
            session.add(category)
            await session.flush()
        for code, name, severity in types:
            existing = await session.scalar(
                select(OffenseTypeModel).where(OffenseTypeModel.code == code)
            )
            if existing:
                offense_by_code[code] = existing
                continue
            offense = OffenseTypeModel(
                id=uuid.uuid4(),
                category_id=category.id,
                code=code,
                name=name,
                default_severity=severity,
                is_cognizable=True,
            )
            session.add(offense)
            await session.flush()
            offense_by_code[code] = offense

    station = await session.scalar(
        select(PoliceStationModel).where(PoliceStationModel.code == "BLR-CENTRAL")
    )
    if station is None:
        raise RuntimeError("BLR-CENTRAL station missing — run identity + socio seed first")

    now = datetime.now(UTC)
    for idx, (station_code, offense_code, lon, lat, days_ago, severity) in enumerate(
        SAMPLE_INCIDENTS
    ):
        external_ref = f"SEED-BLR-{idx + 1:03d}"
        exists = await session.scalar(
            select(IncidentModel).where(IncidentModel.external_ref == external_ref)
        )
        if exists:
            continue
        offense = offense_by_code[offense_code]
        session.add(
            IncidentModel(
                id=uuid.uuid4(),
                external_ref=external_ref,
                offense_type_id=offense.id,
                district_id=station.district_id,
                station_id=station.id,
                status=IncidentStatus.registered,
                severity=severity,
                source=IncidentSource.seed,
                occurred_at=now - timedelta(days=days_ago, hours=idx),
                title=f"{offense.name} near Bengaluru Central",
                description=f"Seeded demo incident for {offense.code}",
                location=point_geography(lon, lat),
                address_text="Bengaluru demo location",
                properties={"seed": True},
            )
        )

    await session.commit()
    print(f"Incident seed complete ({len(SAMPLE_INCIDENTS)} sample rows).")


async def main() -> None:
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        await seed_incidents(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
