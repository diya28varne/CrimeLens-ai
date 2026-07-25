"""Seed Karnataka demo districts + socio-economic / crime metrics for correlation."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.socioeconomics import INDICATOR_CATALOG

from app.infra.db.models import (
    DistrictCrimeMetricModel,
    DistrictModel,
    SocioEconomicIndicatorModel,
)
from app.infra.db.session import get_session_factory

YEAR = 2024

# Demo districts with loosely correlated unemployment ↔ crime_rate for showcase.
DISTRICTS: list[tuple[str, str, dict[str, float], int, float, int]] = [
    # code, name, indicators, incident_count, crime_rate_per_100k, high_severity
    (
        "BLR",
        "Bengaluru City",
        {
            "unemployment_rate": 6.8,
            "literacy_rate": 88.0,
            "population_density": 4381.0,
            "poverty_index": 0.22,
            "urban_pct": 92.0,
        },
        4200,
        318.0,
        410,
    ),
    (
        "MYS",
        "Mysuru",
        {
            "unemployment_rate": 5.4,
            "literacy_rate": 82.0,
            "population_density": 475.0,
            "poverty_index": 0.28,
            "urban_pct": 48.0,
        },
        1100,
        210.0,
        95,
    ),
    (
        "MNG",
        "Mangaluru",
        {
            "unemployment_rate": 5.9,
            "literacy_rate": 86.0,
            "population_density": 1018.0,
            "poverty_index": 0.24,
            "urban_pct": 66.0,
        },
        980,
        245.0,
        88,
    ),
    (
        "HUB",
        "Hubballi-Dharwad",
        {
            "unemployment_rate": 7.5,
            "literacy_rate": 80.0,
            "population_density": 920.0,
            "poverty_index": 0.31,
            "urban_pct": 58.0,
        },
        1500,
        290.0,
        140,
    ),
    (
        "BLG",
        "Belagavi",
        {
            "unemployment_rate": 8.1,
            "literacy_rate": 76.0,
            "population_density": 380.0,
            "poverty_index": 0.36,
            "urban_pct": 32.0,
        },
        1700,
        335.0,
        160,
    ),
    (
        "GLB",
        "Kalaburagi",
        {
            "unemployment_rate": 9.2,
            "literacy_rate": 66.0,
            "population_density": 230.0,
            "poverty_index": 0.44,
            "urban_pct": 28.0,
        },
        1900,
        380.0,
        210,
    ),
    (
        "BGM",
        "Ballari",
        {
            "unemployment_rate": 8.6,
            "literacy_rate": 70.0,
            "population_density": 260.0,
            "poverty_index": 0.40,
            "urban_pct": 35.0,
        },
        1600,
        350.0,
        175,
    ),
    (
        "TUM",
        "Tumakuru",
        {
            "unemployment_rate": 6.2,
            "literacy_rate": 78.0,
            "population_density": 310.0,
            "poverty_index": 0.30,
            "urban_pct": 30.0,
        },
        900,
        230.0,
        70,
    ),
]


async def seed_socio_economic(session: AsyncSession, year: int = YEAR) -> None:
    for code, name, indicators, incidents, rate, high_sev in DISTRICTS:
        district = await session.scalar(select(DistrictModel).where(DistrictModel.code == code))
        if not district:
            district = DistrictModel(id=uuid.uuid4(), code=code, name=name, state_code="KA")
            session.add(district)
            await session.flush()

        for indicator_code, value in indicators.items():
            meta = INDICATOR_CATALOG[indicator_code]
            existing = await session.scalar(
                select(SocioEconomicIndicatorModel).where(
                    SocioEconomicIndicatorModel.district_id == district.id,
                    SocioEconomicIndicatorModel.year == year,
                    SocioEconomicIndicatorModel.indicator_code == indicator_code,
                )
            )
            if existing:
                existing.value = value
                existing.unit = meta["unit"]
                existing.source = "demo-seed"
            else:
                session.add(
                    SocioEconomicIndicatorModel(
                        id=uuid.uuid4(),
                        district_id=district.id,
                        year=year,
                        indicator_code=indicator_code,
                        value=value,
                        unit=meta["unit"],
                        source="demo-seed",
                        properties={},
                    )
                )

        crime = await session.scalar(
            select(DistrictCrimeMetricModel).where(
                DistrictCrimeMetricModel.district_id == district.id,
                DistrictCrimeMetricModel.year == year,
            )
        )
        if crime:
            crime.incident_count = incidents
            crime.crime_rate_per_100k = rate
            crime.high_severity_count = high_sev
        else:
            session.add(
                DistrictCrimeMetricModel(
                    id=uuid.uuid4(),
                    district_id=district.id,
                    year=year,
                    incident_count=incidents,
                    crime_rate_per_100k=rate,
                    high_severity_count=high_sev,
                    properties={"source": "demo-seed"},
                )
            )

    await session.commit()
    print(f"Socio-economic seed complete for year={year} ({len(DISTRICTS)} districts).")


async def main() -> None:
    from app.infra.db.session import get_engine

    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        await seed_socio_economic(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
