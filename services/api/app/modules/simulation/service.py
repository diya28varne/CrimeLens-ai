"""Digital Twin scenario transform — rule-weighted overlays on current predictions."""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext

from app.infra.db.models import (
    HotspotFeatureModel,
    HotspotRunModel,
    ModelRegistryModel,
    PredictionMetric,
    PredictionRunModel,
    PredictionValueModel,
)
from app.modules.simulation.scenarios import (
    DISCLAIMER,
    STATION_COORDS,
    ZONES,
    merge_controls,
)
from app.modules.simulation.schemas import (
    BriefingOut,
    MetricPair,
    MetricsSummary,
    ScenarioControls,
    SectorDelta,
    SimulationPoint,
    SimulationRunData,
    SimulationRunRequest,
)

TIME_MULT = {
    "morning": 0.92,
    "afternoon": 1.00,
    "evening": 1.12,
    "night": 1.22,
}
DAY_MULT = {
    "weekday": 1.00,
    "weekend": 1.10,
    "holiday": 1.08,
}


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _risk_band(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.55:
        return "Medium"
    if score >= 0.35:
        return "Elevated-low"
    return "Low"


def _station_coords(code: str, idx: int) -> tuple[float, float]:
    if code in STATION_COORDS:
        return STATION_COORDS[code]
    # Fan out around Bengaluru center for unknown codes
    angle = (idx * 0.9) % (2 * math.pi)
    return (77.5946 + 0.04 * math.cos(angle), 12.9716 + 0.035 * math.sin(angle))


def _apply_transform(
    baseline: float,
    lon: float,
    lat: float,
    controls: dict[str, Any],
) -> float:
    risk = baseline
    risk *= TIME_MULT.get(controls["time_of_day"], 1.0)
    risk *= DAY_MULT.get(controls["day_type"], 1.0)
    if controls.get("weather_stress"):
        risk *= 1.08

    patrol = float(controls.get("patrol_delta_pct", 0))
    cctv = float(controls.get("cctv_delta_pct", 0))
    # More patrol / CCTV reduces risk; cuts reduce coverage → risk up
    risk *= 1.0 - 0.28 * (patrol / 100.0)
    risk *= 1.0 - 0.18 * (cctv / 100.0)

    zone_key = controls.get("event_zone", "central")
    zone = ZONES.get(zone_key, ZONES["central"])
    dist = _haversine_km(lon, lat, zone["lon"], zone["lat"])
    in_zone = dist <= float(zone["radius_km"])
    near_zone = dist <= float(zone["radius_km"]) * 1.6

    if controls.get("public_event"):
        if in_zone:
            risk *= 1.28
        elif near_zone:
            risk *= 1.12

    # Metro disruption / VIP corridor gets extra spillover when event on metro zone
    if controls.get("public_event") and zone_key == "metro_corridor_a" and near_zone:
        risk *= 1.06

    if controls.get("day_type") == "holiday" and zone_key in {"south", "east"} and near_zone:
        risk *= 1.05

    return _clamp(risk)


def _metrics_from_points(
    risks: list[float],
    controls: dict[str, Any],
    *,
    threshold: float = 0.6,
) -> MetricsSummary:
    if not risks:
        agg = 0.0
        hot = 0
    else:
        agg = sum(risks) / len(risks)
        hot = sum(1 for r in risks if r >= threshold)

    patrol = float(controls.get("patrol_delta_pct", 0))
    cctv = float(controls.get("cctv_delta_pct", 0))
    # Coverage index 0–100 centered at 50 when sliders are 0
    patrol_coverage = _clamp(50 + patrol * 0.7 + (8 if not controls.get("public_event") else 0), 0, 100)
    utilization = _clamp(40 + abs(patrol) * 0.45 + abs(cctv) * 0.35, 0, 100)
    # Relative ops cost rises with resource levers and event staffing
    cost = _clamp(
        35
        + max(0, patrol) * 0.55
        + max(0, cctv) * 0.4
        + (12 if controls.get("public_event") else 0)
        + (6 if controls.get("weather_stress") else 0),
        0,
        100,
    )
    return MetricsSummary(
        aggregate_risk=round(agg, 4),
        hotspot_count=hot,
        patrol_coverage=round(patrol_coverage, 1),
        resource_utilization=round(utilization, 1),
        ops_cost_index=round(cost, 1),
    )


def _build_briefing(
    label: str,
    baseline: MetricsSummary,
    simulated: MetricsSummary,
    sector_deltas: list[SectorDelta],
    controls: dict[str, Any],
) -> BriefingOut:
    changes: list[str] = []
    for d in sector_deltas[:4]:
        sign = "+" if d.pct_change > 0 else ""
        changes.append(f"{sign}{d.pct_change:.0f}% {d.direction} — {d.sector}: {d.note}")
    if not changes:
        changes.append("No material sector shift under current levers.")

    actions: list[str] = []
    if simulated.aggregate_risk > baseline.aggregate_risk:
        actions.append("Add 1–2 mobile patrols on the highest-delta corridors.")
        if controls.get("public_event"):
            actions.append(f"Tighten perimeter CCTV around {ZONES[controls['event_zone']]['label']}.")
        actions.append("Stand up a short-interval watch desk for the scenario window.")
    else:
        actions.append("Hold surge capacity; reallocate surplus patrol to neighboring beats.")
        actions.append("Keep CCTV emphasis on residual medium-risk cells.")
        actions.append("Document the scenario for after-action comparison.")

    # Confidence: higher when fewer extreme levers and baseline data present
    extremity = (abs(float(controls["patrol_delta_pct"])) + abs(float(controls["cctv_delta_pct"]))) / 100.0
    confidence = _clamp(0.93 - 0.12 * extremity - (0.04 if controls.get("weather_stress") else 0), 0.72, 0.94)

    return BriefingOut(
        scenario_label=label,
        current_risk_band=_risk_band(simulated.aggregate_risk),
        predicted_changes=changes,
        suggested_actions=actions[:3],
        confidence=round(confidence, 2),
        disclaimer=DISCLAIMER,
    )


class SimulationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_scenarios(self, ctx: AuthContext) -> list[dict[str, Any]]:
        _ = ctx
        from app.modules.simulation.scenarios import SCENARIO_PRESETS

        return [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p["description"],
                "controls": ScenarioControls(**p["controls"]),
            }
            for p in SCENARIO_PRESETS
        ]

    async def _baseline_points(self, district_id: Any | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        # Prefer current station risk scores + hotspot centroids
        stmt = (
            select(PredictionRunModel, ModelRegistryModel)
            .join(ModelRegistryModel, ModelRegistryModel.id == PredictionRunModel.model_id)
            .where(
                PredictionRunModel.is_current.is_(True),
                PredictionRunModel.metric == PredictionMetric.risk_score,
            )
            .order_by(PredictionRunModel.generated_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        source: dict[str, Any] = {"prediction_run_id": None, "hotspot_run_id": None, "model": None}
        points: list[dict[str, Any]] = []

        if row:
            run, model = row
            source["prediction_run_id"] = str(run.id)
            source["model"] = f"{model.model_code}@{model.model_version}"
            vstmt = (
                select(PredictionValueModel)
                .where(PredictionValueModel.prediction_run_id == run.id)
                .order_by(PredictionValueModel.value.desc())
                .limit(40)
            )
            if district_id:
                vstmt = vstmt.where(PredictionValueModel.district_id == district_id)
            values = (await self._session.execute(vstmt)).scalars().all()
            for idx, v in enumerate(values):
                props = v.properties or {}
                code = str(props.get("station_code") or f"ST-{idx}")
                name = str(props.get("station_name") or code)
                lon, lat = _station_coords(code, idx)
                points.append(
                    {
                        "id": str(v.id),
                        "kind": "station",
                        "label": name,
                        "lon": lon,
                        "lat": lat,
                        "baseline_risk": float(v.value),
                        "sector_hint": code,
                    }
                )

        hstmt = select(HotspotRunModel).where(HotspotRunModel.is_current.is_(True))
        if district_id:
            hstmt = hstmt.where(HotspotRunModel.district_id == district_id)
        hstmt = hstmt.order_by(HotspotRunModel.created_at.desc()).limit(1)
        hotspot_run = await self._session.scalar(hstmt)
        if hotspot_run:
            source["hotspot_run_id"] = str(hotspot_run.id)
            features = (
                await self._session.execute(
                    select(HotspotFeatureModel)
                    .where(HotspotFeatureModel.hotspot_run_id == hotspot_run.id)
                    .order_by(HotspotFeatureModel.rank.asc())
                    .limit(20)
                )
            ).scalars().all()
            for f in features:
                props = f.properties or {}
                lon = props.get("lon")
                lat = props.get("lat")
                if lon is None or lat is None:
                    continue
                points.append(
                    {
                        "id": str(f.id),
                        "kind": "hotspot",
                        "label": str(props.get("label") or f"Hotspot #{f.rank}"),
                        "lon": float(lon),
                        "lat": float(lat),
                        "baseline_risk": float(f.score),
                        "sector_hint": str(props.get("label") or "hotspot"),
                    }
                )

        # Demo fallback if DB empty
        if not points:
            for i, (code, (lon, lat)) in enumerate(STATION_COORDS.items()):
                points.append(
                    {
                        "id": f"demo-{code}",
                        "kind": "station",
                        "label": code.replace("BLR-", "").title(),
                        "lon": lon,
                        "lat": lat,
                        "baseline_risk": round(0.45 + (i * 0.07) % 0.4, 3),
                        "sector_hint": code,
                    }
                )
            source["model"] = "demo-fallback"

        return points, source

    async def run(self, ctx: AuthContext, body: SimulationRunRequest) -> SimulationRunData:
        _ = ctx
        overrides = body.controls.model_dump() if body.controls else None
        label, controls = merge_controls(body.preset_id, overrides)
        # If client sent full controls without preset, prefer those exactly
        if body.controls and not body.preset_id:
            controls = body.controls.model_dump()
            label = "Custom scenario"
        elif body.controls and body.preset_id:
            controls = {**controls, **body.controls.model_dump()}

        raw_points, source = await self._baseline_points(body.district_id)

        baseline_controls = {
            "patrol_delta_pct": 0,
            "cctv_delta_pct": 0,
            "public_event": False,
            "event_zone": controls["event_zone"],
            "time_of_day": "afternoon",
            "day_type": "weekday",
            "weather_stress": False,
        }

        sim_points: list[SimulationPoint] = []
        sector_acc: dict[str, list[float]] = {}

        for p in raw_points:
            b = float(p["baseline_risk"])
            # Normalize baseline to "current ops afternoon weekday" framing
            base_adj = _apply_transform(b, p["lon"], p["lat"], baseline_controls)
            sim = _apply_transform(b, p["lon"], p["lat"], controls)
            delta = sim - base_adj
            delta_pct = (delta / base_adj * 100.0) if base_adj > 1e-6 else 0.0
            sim_points.append(
                SimulationPoint(
                    id=p["id"],
                    kind=p["kind"],
                    label=p["label"],
                    lon=p["lon"],
                    lat=p["lat"],
                    baseline_risk=round(base_adj, 4),
                    simulated_risk=round(sim, 4),
                    delta=round(delta, 4),
                    delta_pct=round(delta_pct, 2),
                )
            )
            zone = ZONES[controls["event_zone"]]
            dist = _haversine_km(p["lon"], p["lat"], zone["lon"], zone["lat"])
            sector = zone["label"] if dist <= zone["radius_km"] * 1.6 else "Rest of city"
            sector_acc.setdefault(sector, []).append(delta_pct)

        base_metrics = _metrics_from_points(
            [p.baseline_risk for p in sim_points], baseline_controls
        )
        sim_metrics = _metrics_from_points(
            [p.simulated_risk for p in sim_points], controls
        )

        deltas: list[SectorDelta] = []
        for sector, pcts in sorted(sector_acc.items(), key=lambda kv: -abs(sum(kv[1]) / len(kv[1]))):
            avg = sum(pcts) / len(pcts)
            direction: Any = "flat"
            if avg > 1.5:
                direction = "up"
            elif avg < -1.5:
                direction = "down"
            note = (
                "Crowd / corridor pressure elevates residual risk"
                if direction == "up"
                else "Coverage levers suppress projected risk"
                if direction == "down"
                else "Limited net movement"
            )
            deltas.append(
                SectorDelta(
                    sector=sector,
                    pct_change=round(avg, 1),
                    direction=direction,
                    note=note,
                )
            )

        comparison = [
            MetricPair(
                key="aggregate_risk",
                label="Crime risk (avg)",
                baseline=base_metrics.aggregate_risk,
                simulated=sim_metrics.aggregate_risk,
                unit="score",
                higher_is_better=False,
            ),
            MetricPair(
                key="hotspot_count",
                label="Cells above risk threshold",
                baseline=float(base_metrics.hotspot_count),
                simulated=float(sim_metrics.hotspot_count),
                unit="count",
                higher_is_better=False,
            ),
            MetricPair(
                key="patrol_coverage",
                label="Patrol coverage index",
                baseline=base_metrics.patrol_coverage,
                simulated=sim_metrics.patrol_coverage,
                unit="index",
                higher_is_better=True,
            ),
            MetricPair(
                key="resource_utilization",
                label="Resource utilization",
                baseline=base_metrics.resource_utilization,
                simulated=sim_metrics.resource_utilization,
                unit="index",
                higher_is_better=None,
            ),
            MetricPair(
                key="ops_cost_index",
                label="Est. relative ops cost",
                baseline=base_metrics.ops_cost_index,
                simulated=sim_metrics.ops_cost_index,
                unit="index",
                higher_is_better=False,
            ),
        ]

        briefing = _build_briefing(label, base_metrics, sim_metrics, deltas, controls)
        zone = ZONES[controls["event_zone"]]

        return SimulationRunData(
            run_id=str(uuid.uuid4()),
            scenario_label=label,
            preset_id=body.preset_id,
            controls=ScenarioControls(**controls),
            baseline=base_metrics,
            simulated=sim_metrics,
            comparison=comparison,
            deltas=deltas,
            points=sim_points,
            event_zone={
                "id": controls["event_zone"],
                "label": zone["label"],
                "lon": zone["lon"],
                "lat": zone["lat"],
                "radius_km": zone["radius_km"],
            },
            briefing=briefing,
            confidence=briefing.confidence,
            disclaimer=DISCLAIMER,
            source=source,
        )
