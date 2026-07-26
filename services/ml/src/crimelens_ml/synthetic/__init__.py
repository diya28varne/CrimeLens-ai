"""Domain-inspired synthetic world for CrimeLens (Karnataka-scoped).

Generates coherent cell-level risk frames and hotspot grids — not i.i.d. noise.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from crimelens_ml.feature_engineering import derive_risk_labels, engineer_risk_features
from crimelens_ml.preprocessing import add_cyclical_time, validate_coordinates
from crimelens_ml.utils import geohash_encode, load_common_config, new_run_id
from crimelens_ml.utils.io import write_parquet

# Seeded district hubs (demo geometry aligned with CrimeLens seed narrative)
DISTRICTS: list[dict[str, Any]] = [
    {"code": "BLR-U", "name": "Bengaluru Urban", "lon": 77.59, "lat": 12.97, "urban": 1, "density": 4500},
    {"code": "MYS", "name": "Mysuru", "lon": 76.64, "lat": 12.30, "urban": 1, "density": 1200},
    {"code": "MNG", "name": "Mangaluru", "lon": 74.85, "lat": 12.91, "urban": 1, "density": 1100},
    {"code": "HBL", "name": "Hubballi", "lon": 75.13, "lat": 15.36, "urban": 1, "density": 900},
    {"code": "BGM", "name": "Belagavi", "lon": 74.50, "lat": 15.85, "urban": 0, "density": 500},
    {"code": "KLR", "name": "Kolar", "lon": 78.13, "lat": 13.13, "urban": 0, "density": 400},
]


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_risk_world(
    n_cells: int = 480,
    n_days: int = 45,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate cell × day observations with spatial clustering and temporal regimes."""
    cfg = load_common_config()
    rng = _rng(seed)
    rows: list[dict[str, Any]] = []
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=n_days)

    # Pre-place hotspot centres per district
    centres = []
    for d in DISTRICTS:
        for _ in range(3):
            centres.append(
                (
                    d,
                    d["lon"] + rng.normal(0, 0.08),
                    d["lat"] + rng.normal(0, 0.08),
                    rng.uniform(0.6, 1.0),
                )
            )

    for i in range(n_cells):
        d = DISTRICTS[i % len(DISTRICTS)]
        # Mix background cells + hotspot-near cells
        if rng.random() < 0.35:
            c = centres[rng.integers(0, len(centres))]
            lon = c[1] + rng.normal(0, 0.015)
            lat = c[2] + rng.normal(0, 0.015)
            hotspot_boost = float(c[3])
        else:
            lon = d["lon"] + rng.normal(0, 0.12)
            lat = d["lat"] + rng.normal(0, 0.12)
            hotspot_boost = 0.15

        station_code = f"{d['code']}-PS-{(i % 8) + 1:02d}"
        geohash = geohash_encode(lat, lon, cfg.get("geohash_precision", 7))

        base_7 = max(0, rng.poisson(2 + 6 * hotspot_boost * d["urban"]))
        for day in range(n_days):
            ts = start + timedelta(days=day)
            hour = int(rng.choice([2, 9, 14, 18, 22], p=[0.15, 0.2, 0.2, 0.25, 0.2]))
            is_weekend = ts.weekday() >= 5
            is_night = hour >= 20 or hour <= 5
            festival = 1 if (day % 17 == 0 or day % 23 == 0) else 0

            # Temporal multipliers
            mult = 1.0
            mult *= 1.25 if is_weekend else 1.0
            mult *= 1.35 if is_night else 0.95
            mult *= 1.5 if festival else 1.0
            mult *= 1.1 + 0.15 * np.sin(2 * np.pi * day / 7)

            incidents_7d = max(0, int(rng.poisson(base_7 * mult)))
            incidents_30d = max(incidents_7d, int(incidents_7d * rng.uniform(3.2, 4.5)))
            weekend_cnt = int(incidents_30d * (0.40 if is_weekend else 0.28) * rng.uniform(0.8, 1.2))
            night_cnt = int(incidents_30d * (0.45 if is_night else 0.30) * rng.uniform(0.8, 1.2))

            precip = max(0.0, float(rng.gamma(1.2, 3.0) if rng.random() < 0.25 else rng.uniform(0, 2)))
            traffic = float(np.clip(0.3 + 0.5 * hotspot_boost + 0.2 * d["urban"] + rng.normal(0, 0.05), 0, 1))
            patrol = float(np.clip(8 + rng.normal(0, 3) - 4 * hotspot_boost + 3 * d["urban"], 1, 40))
            cctv = float(np.clip(rng.normal(6 + 8 * d["urban"] - 3 * (1 - hotspot_boost), 2), 0, 30))

            rows.append(
                {
                    "district_code": d["code"],
                    "district_name": d["name"],
                    "station_code": station_code,
                    "grid_cell_id": f"G-{geohash}",
                    "geohash": geohash,
                    "centroid_lon": lon,
                    "centroid_lat": lat,
                    "as_of_ts": ts.isoformat(),
                    "hour": hour,
                    "is_weekend": int(is_weekend),
                    "is_night": int(is_night),
                    "festival_flag": festival,
                    "festival_lift": 0.55 if festival else 0.1,
                    "incidents_7d": incidents_7d,
                    "incidents_30d": incidents_30d,
                    "weekend_cnt_30d": weekend_cnt,
                    "night_cnt_30d": night_cnt,
                    "severity_high_crit_share_7d": float(np.clip(0.1 + 0.4 * hotspot_boost + rng.normal(0, 0.05), 0, 1)),
                    "temp_c": float(rng.normal(28, 3)),
                    "precip_mm": precip,
                    "visibility_km": float(np.clip(rng.normal(8 - precip / 10, 1.5), 1, 12)),
                    "traffic_index": traffic,
                    "population_flow_index": float(np.clip(traffic * rng.uniform(0.7, 1.1), 0, 1)),
                    "lighting_index": float(np.clip(rng.normal(0.55 + 0.2 * d["urban"], 0.1), 0, 1)),
                    "road_connectivity_score": float(np.clip(rng.normal(0.5 + 0.25 * d["urban"], 0.1), 0, 1)),
                    "travel_impedance": float(np.clip(rng.normal(0.35, 0.1), 0.05, 1)),
                    "cctv_density": cctv,
                    "patrol_hours_7d": patrol,
                    "patrol_density": float(np.clip(patrol / 40.0, 0, 1)),
                    "avg_response_minutes": float(np.clip(rng.normal(22 + 10 * hotspot_boost - 5 * d["urban"], 5), 5, 90)),
                    "dist_market_m": float(np.clip(rng.lognormal(7.2, 0.5) * (1.2 - hotspot_boost), 50, 8000)),
                    "dist_school_m": float(np.clip(rng.lognormal(7.0, 0.45), 80, 7000)),
                    "footfall_index": float(np.clip(0.3 + 0.5 * hotspot_boost + rng.normal(0, 0.05), 0, 1)),
                    "repeat_offender_activity_score": float(np.clip(0.15 + 0.55 * hotspot_boost + rng.normal(0, 0.05), 0, 1)),
                    "hotspot_days": float(np.clip(rng.normal(5 + 18 * hotspot_boost, 3), 0, 30)),
                    "population_density": float(d["density"] * rng.uniform(0.7, 1.3)),
                    "unemployment_rate": float(np.clip(rng.normal(5.5 + 2.5 * (1 - d["urban"]), 1.2), 2, 18)),
                    "poverty_index": float(np.clip(rng.normal(0.22 + 0.1 * (1 - d["urban"]), 0.05), 0.05, 0.7)),
                    "literacy_rate": float(np.clip(rng.normal(78 + 8 * d["urban"], 4), 55, 95)),
                    "urban_pct": float(70 if d["urban"] else 35),
                    "provenance": "synthetic",
                    "horizon_hours": 168,
                }
            )

    raw = pd.DataFrame(rows)
    raw = validate_coordinates(raw)
    raw = add_cyclical_time(raw, "hour")
    engineered = engineer_risk_features(raw)
    labeled = derive_risk_labels(engineered)
    labeled["feature_set_id"] = cfg.get("feature_set_id", "risk_v1")
    labeled["world_run_id"] = new_run_id("synth")
    return labeled


def generate_hotspot_frame(risk_df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Collapse latest day per cell into hotspot evolution features (Dataset D2)."""
    rng = _rng(seed)
    latest_ts = risk_df["as_of_ts"].max()
    snap = risk_df[risk_df["as_of_ts"] == latest_ts].copy()
    snap["incident_density"] = snap["CrimeFrequency7Days"].astype(float)
    snap["historical_density_30d"] = snap["CrimeFrequency30Days"].astype(float)
    snap["festival_impact"] = snap["FestivalImpactScore"]
    snap["weather_impact"] = snap["WeatherRiskIndex"]
    snap["density_delta_7d"] = snap["CrimeFrequency7Days"] - (snap["CrimeFrequency30Days"] / 4.0)
    snap["density_delta_30d"] = snap["CrimeFrequency30Days"] - snap["CrimeFrequency30Days"].median()

    # Growth label from deltas
    growth = []
    for _, r in snap.iterrows():
        d7 = float(r["density_delta_7d"])
        if d7 > 1.5:
            growth.append("Growing")
        elif d7 < -1.0:
            growth.append("Shrinking")
        else:
            growth.append("Stable")
    snap["hotspot_growth"] = growth
    snap["noise"] = rng.normal(0, 0.01, len(snap))
    return snap.reset_index(drop=True)


def materialize_synthetic(n_cells: int = 480, n_days: int = 45, seed: int = 42) -> dict[str, str]:
    """Write raw/processed/engineered/synthetic Parquet snapshots."""
    from crimelens_ml.utils import ensure_dirs

    paths = ensure_dirs()
    run_id = new_run_id("world")
    risk = generate_risk_world(n_cells=n_cells, n_days=n_days, seed=seed)
    hotspot = generate_hotspot_frame(risk, seed=seed)

    # Layered store
    raw_path = write_parquet(risk.drop(columns=[c for c in risk.columns if c[0].isupper() or c.endswith("Score") or c.endswith("Index") or c.endswith("Ratio")], errors="ignore"), paths["raw"] / f"risk_cells_{run_id}.parquet")
    # Keep full engineered
    eng_path = write_parquet(risk, paths["engineered"] / "risk_intelligence" / f"{run_id}.parquet")
    syn_path = write_parquet(risk, paths["synthetic"] / f"risk_world_{run_id}.parquet")
    hot_path = write_parquet(hotspot, paths["engineered"] / "hotspot_evolution" / f"{run_id}.parquet")
    proc_path = write_parquet(risk[["district_code", "station_code", "grid_cell_id", "as_of_ts", "geohash", "risk_level", "risk_score"]], paths["processed"] / f"risk_labels_{run_id}.parquet")

    # Latest pointers
    write_parquet(risk, paths["engineered"] / "risk_intelligence" / "latest.parquet")
    write_parquet(hotspot, paths["engineered"] / "hotspot_evolution" / "latest.parquet")

    return {
        "run_id": run_id,
        "raw": str(raw_path),
        "processed": str(proc_path),
        "engineered_risk": str(eng_path),
        "engineered_hotspot": str(hot_path),
        "synthetic": str(syn_path),
        "n_risk_rows": str(len(risk)),
        "n_hotspot_rows": str(len(hotspot)),
    }
