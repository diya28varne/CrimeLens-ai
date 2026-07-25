"""Seed demo risk model, station scores, SHAP artifacts, and hotspots."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.async_runtime import run_async
from app.infra.db.geo import point_geography
from app.infra.db.models import (
    DistrictModel,
    ExplanationArtifactModel,
    HotspotFeatureModel,
    HotspotMethod,
    HotspotRunModel,
    ModelRegistryModel,
    ModelStatus,
    ModelTask,
    PoliceStationModel,
    PredictionMetric,
    PredictionRunModel,
    PredictionScopeType,
    PredictionValueModel,
)
from app.infra.db.session import get_engine, get_session_factory


async def seed_predictions(session: AsyncSession) -> None:
    district = await session.scalar(select(DistrictModel).where(DistrictModel.code == "BLR"))
    if district is None:
        raise RuntimeError("BLR district missing — run identity/socio seed first")

    stations = list(
        (
            await session.execute(
                select(PoliceStationModel).where(PoliceStationModel.district_id == district.id)
            )
        ).scalars().all()
    )
    if not stations:
        raise RuntimeError("No stations for BLR")

    # Ensure a few stations so the risk chart looks meaningful in demo
    extra = [
        ("BLR-EAST", "Bengaluru East"),
        ("BLR-WEST", "Bengaluru West"),
        ("BLR-NORTH", "Bengaluru North"),
        ("BLR-SOUTH", "Bengaluru South"),
    ]
    for code, name in extra:
        exists = await session.scalar(
            select(PoliceStationModel).where(
                PoliceStationModel.district_id == district.id,
                PoliceStationModel.code == code,
            )
        )
        if exists:
            stations.append(exists)
            continue
        st = PoliceStationModel(
            id=uuid.uuid4(),
            district_id=district.id,
            code=code,
            name=name,
            is_active=True,
        )
        session.add(st)
        await session.flush()
        stations.append(st)

    existing = await session.scalar(
        select(ModelRegistryModel).where(
            ModelRegistryModel.model_code == "risk_lgbm",
            ModelRegistryModel.model_version == "2026.07.24",
        )
    )
    if existing:
        return

    now = datetime.now(UTC)
    model = ModelRegistryModel(
        id=uuid.uuid4(),
        model_code="risk_lgbm",
        model_version="2026.07.24",
        task=ModelTask.risk,
        algorithm="lightgbm",
        status=ModelStatus.production,
        train_window_start=now - timedelta(days=90),
        train_window_end=now - timedelta(days=1),
        metrics={"pr_auc": 0.78, "brier": 0.14},
        feature_list=["lag_7d_count", "weekend_flag", "severity_share_high", "hour_of_day"],
    )
    session.add(model)
    await session.flush()

    run = PredictionRunModel(
        id=uuid.uuid4(),
        model_id=model.id,
        scope_type=PredictionScopeType.station,
        metric=PredictionMetric.risk_score,
        horizon_start=now,
        horizon_end=now + timedelta(days=7),
        generated_at=now,
        is_current=True,
        notes="Demo risk scores derived from seeded incident density heuristics.",
    )
    session.add(run)
    await session.flush()

    demo_scores = [
        (0.82, "Central beat elevated"),
        (0.71, "Night-time property cluster"),
        (0.64, "Moderate residual risk"),
        (0.55, "Baseline watch"),
        (0.48, "Below average"),
    ]

    for idx, station in enumerate(stations):
        score, label = demo_scores[idx % len(demo_scores)]
        # Slight variation by station order
        score = min(0.95, score + (idx * 0.01))
        value = PredictionValueModel(
            id=uuid.uuid4(),
            prediction_run_id=run.id,
            district_id=district.id,
            station_id=station.id,
            value=round(score, 3),
            lower_bound=round(max(0.0, score - 0.08), 3),
            upper_bound=round(min(1.0, score + 0.08), 3),
            occurs_on=now.date(),
            properties={
                "station_code": station.code,
                "station_name": station.name,
                "label": label,
            },
        )
        session.add(value)
        await session.flush()

        session.add(
            ExplanationArtifactModel(
                id=uuid.uuid4(),
                prediction_run_id=run.id,
                prediction_value_id=value.id,
                shap_global={
                    "features": [
                        {"feature": "lag_7d_count", "importance": 0.32},
                        {"feature": "severity_share_high", "importance": 0.24},
                        {"feature": "weekend_flag", "importance": 0.18},
                        {"feature": "hour_of_day", "importance": 0.14},
                    ]
                },
                shap_local={
                    "base_value": 0.42,
                    "contributions": [
                        {"feature": "lag_7d_count", "value": 6 + idx, "contribution": 0.18},
                        {"feature": "severity_share_high", "value": 0.35, "contribution": 0.12},
                        {"feature": "weekend_flag", "value": 1, "contribution": 0.06},
                        {"feature": "hour_of_day", "value": 21, "contribution": 0.04},
                    ],
                },
                summary_text=(
                    f"Risk at {station.name} elevated primarily due to 7-day incident lag "
                    "and high-severity share. Treat as decision support, not disposition."
                ),
            )
        )

    # Clear other current hotspot runs for district then insert
    await session.execute(
        update(HotspotRunModel)
        .where(HotspotRunModel.district_id == district.id, HotspotRunModel.is_current.is_(True))
        .values(is_current=False)
    )

    hotspot_run = HotspotRunModel(
        id=uuid.uuid4(),
        method=HotspotMethod.grid_density,
        model_version="kde-demo-1",
        district_id=district.id,
        window_start=now - timedelta(days=30),
        window_end=now,
        params={"bandwidth_m": 400},
        metrics={"clusters": 3},
        is_current=True,
    )
    session.add(hotspot_run)
    await session.flush()

    hotspots = [
        (1, 0.91, 5, 77.5946, 12.9716, "MG Road cluster"),
        (2, 0.77, 3, 77.5800, 12.9650, "Cubbon area"),
        (3, 0.68, 2, 77.6050, 12.9800, "Indiranagar fringe"),
    ]
    for rank, score, count, lon, lat, label in hotspots:
        pt = WKTElement(f"POINT({lon} {lat})", srid=4326)
        session.add(
            HotspotFeatureModel(
                id=uuid.uuid4(),
                hotspot_run_id=hotspot_run.id,
                rank=rank,
                score=score,
                incident_count=count,
                geom=pt,
                centroid=point_geography(lon, lat),
                properties={"lon": lon, "lat": lat, "label": label},
            )
        )

    await session.commit()


async def main() -> None:
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        await seed_predictions(session)
    await engine.dispose()
    print("Prediction seed complete.")


if __name__ == "__main__":
    run_async(main())
