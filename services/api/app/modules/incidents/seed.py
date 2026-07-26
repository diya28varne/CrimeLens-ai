"""Seed offense taxonomy + sample Karnataka incidents (PostGIS points)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.async_runtime import run_async
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
# Includes a ~90-day arc: sparse → cluster → hotspot → neighboring spillover → easing
SAMPLE_INCIDENTS: list[tuple[str, str, float, float, int, SeverityLevel]] = [
    # Original near-term samples
    ("BLR-CENTRAL", "THEFT", 77.5946, 12.9716, 2, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.5800, 12.9650, 5, SeverityLevel.high),
    ("BLR-CENTRAL", "CYBER_FRAUD", 77.6000, 12.9800, 1, SeverityLevel.medium),
    ("BLR-CENTRAL", "ASSAULT", 77.5900, 12.9600, 8, SeverityLevel.high),
    ("BLR-CENTRAL", "ROBBERY", 77.5850, 12.9750, 12, SeverityLevel.critical),
    ("BLR-CENTRAL", "THEFT", 77.6050, 12.9700, 3, SeverityLevel.low),
    ("BLR-CENTRAL", "THEFT", 77.5700, 12.9550, 15, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.6100, 12.9850, 20, SeverityLevel.high),
    # Early sparse (≈90–70 days ago)
    ("BLR-CENTRAL", "THEFT", 77.5920, 12.9680, 88, SeverityLevel.low),
    ("BLR-CENTRAL", "THEFT", 77.5980, 12.9740, 82, SeverityLevel.medium),
    ("BLR-CENTRAL", "CYBER_FRAUD", 77.6010, 12.9770, 76, SeverityLevel.medium),
    # Growing MG Road cluster (≈65–45 days)
    ("BLR-CENTRAL", "THEFT", 77.5940, 12.9710, 65, SeverityLevel.medium),
    ("BLR-CENTRAL", "THEFT", 77.5955, 12.9725, 62, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.5935, 12.9705, 58, SeverityLevel.high),
    ("BLR-CENTRAL", "THEFT", 77.5960, 12.9718, 55, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.5948, 12.9722, 52, SeverityLevel.high),
    ("BLR-CENTRAL", "ROBBERY", 77.5952, 12.9714, 48, SeverityLevel.critical),
    ("BLR-CENTRAL", "THEFT", 77.5930, 12.9730, 45, SeverityLevel.medium),
    # Spike + spillover east (≈42–28 days) — festival window story
    ("BLR-CENTRAL", "THEFT", 77.6040, 12.9790, 42, SeverityLevel.medium),
    ("BLR-CENTRAL", "THEFT", 77.6060, 12.9810, 40, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.6055, 12.9805, 38, SeverityLevel.high),
    ("BLR-CENTRAL", "THEFT", 77.6070, 12.9785, 36, SeverityLevel.medium),
    ("BLR-CENTRAL", "ASSAULT", 77.6035, 12.9820, 34, SeverityLevel.high),
    ("BLR-CENTRAL", "BURGLARY", 77.6045, 12.9795, 32, SeverityLevel.high),
    ("BLR-CENTRAL", "THEFT", 77.6080, 12.9800, 30, SeverityLevel.medium),
    ("BLR-CENTRAL", "THEFT", 77.6020, 12.9780, 28, SeverityLevel.low),
    # Intervention / easing narrative (≈25–10 days) — fewer near core
    ("BLR-CENTRAL", "THEFT", 77.5500, 12.9700, 24, SeverityLevel.medium),
    ("BLR-CENTRAL", "CYBER_FRAUD", 77.5520, 12.9680, 22, SeverityLevel.medium),
    ("BLR-CENTRAL", "THEFT", 77.6400, 12.9780, 18, SeverityLevel.medium),
    ("BLR-CENTRAL", "BURGLARY", 77.5950, 12.9100, 16, SeverityLevel.high),
    ("BLR-CENTRAL", "THEFT", 77.5910, 12.9690, 14, SeverityLevel.low),
    ("BLR-CENTRAL", "ASSAULT", 77.5890, 13.0200, 11, SeverityLevel.high),
    ("BLR-CENTRAL", "THEFT", 77.5965, 12.9728, 9, SeverityLevel.medium),
    ("BLR-CENTRAL", "THEFT", 77.5975, 12.9702, 7, SeverityLevel.low),
    ("BLR-CENTRAL", "BURGLARY", 77.5810, 12.9660, 6, SeverityLevel.high),
    ("BLR-CENTRAL", "THEFT", 77.6065, 12.9695, 4, SeverityLevel.medium),
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
    run_async(main())
