"""Police resource optimization (D6) — OR-Tools CP-SAT if available, else greedy coverage."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from crimelens_ml.utils import load_yaml, ml_root, new_run_id, write_json
from crimelens_ml.utils.io import read_parquet, write_parquet


def _load_cells() -> pd.DataFrame:
    path = ml_root() / "datasets" / "engineered" / "hotspot_evolution" / "latest.parquet"
    if not path.exists():
        path = ml_root() / "datasets" / "engineered" / "risk_intelligence" / "latest.parquet"
        if not path.exists():
            from crimelens_ml.synthetic import materialize_synthetic

            materialize_synthetic()
            path = ml_root() / "datasets" / "engineered" / "hotspot_evolution" / "latest.parquet"
    df = read_parquet(path)
    # latest day only if multi-day
    if "as_of_ts" in df.columns:
        latest = df["as_of_ts"].max()
        df = df[df["as_of_ts"] == latest].copy()
    return df.reset_index(drop=True)


def _score_zone(row: pd.Series, weights: dict[str, float]) -> float:
    hotspot = float(row.get("HotspotPersistenceScore", row.get("risk_score", 0.4)))
    density = float(row.get("incident_density", row.get("CrimeFrequency7Days", 1)))
    density_n = min(density / 20.0, 1.0)
    gap = 1.0 - float(row.get("PatrolCoverageIndex", 0.5))
    event = float(row.get("FestivalImpactScore", row.get("festival_impact", 0)))
    return (
        weights.get("hotspot_score", 0.45) * hotspot
        + weights.get("crime_density", 0.30) * density_n
        + weights.get("coverage_gap", 0.15) * gap
        + weights.get("event_load", 0.10) * event
    )


def _greedy_optimize(df: pd.DataFrame, cfg: dict[str, Any], officers: int, vehicles: int) -> dict[str, Any]:
    weights = cfg.get("objective_weights", {})
    max_zones = int(cfg.get("constraints", {}).get("max_zones_per_shift", 3))
    min_officers = int(cfg.get("constraints", {}).get("min_officers_per_zone", 2))

    scored = df.copy()
    scored["zone_score"] = scored.apply(lambda r: _score_zone(r, weights), axis=1)
    ranked = scored.sort_values("zone_score", ascending=False)

    assignments = []
    remaining_officers = officers
    remaining_vehicles = vehicles
    for _, row in ranked.iterrows():
        if len(assignments) >= max_zones:
            break
        need = min_officers
        if remaining_officers < need or remaining_vehicles < 1:
            break
        remaining_officers -= need
        remaining_vehicles -= 1
        assignments.append(
            {
                "station_code": row.get("station_code"),
                "grid_cell_id": row.get("grid_cell_id"),
                "district_code": row.get("district_code"),
                "zone_score": float(row["zone_score"]),
                "officers_assigned": need,
                "vehicles_assigned": 1,
                "best_patrol_zone": row.get("grid_cell_id"),
                "best_shift": _pick_shift(row),
                "best_patrol_route": f"ROUTE-{row.get('station_code')}-{row.get('grid_cell_id')}",
            }
        )

    return {
        "solver": "greedy_coverage",
        "assignments": assignments,
        "unassigned_officers": remaining_officers,
        "unassigned_vehicles": remaining_vehicles,
        "objective_estimate": float(sum(a["zone_score"] for a in assignments)),
    }


def _pick_shift(row: pd.Series) -> str:
    night = float(row.get("NightCrimeRatio", 0.3))
    if night >= 0.45:
        return "night"
    if float(row.get("FestivalImpactScore", 0)) > 0.4:
        return "afternoon"
    return "morning"


def _ortools_optimize(df: pd.DataFrame, cfg: dict[str, Any], officers: int, vehicles: int) -> dict[str, Any] | None:
    try:
        from ortools.sat.python import cp_model
    except Exception:
        return None

    weights = cfg.get("objective_weights", {})
    max_zones = int(cfg.get("constraints", {}).get("max_zones_per_shift", 3))
    min_officers = int(cfg.get("constraints", {}).get("min_officers_per_zone", 2))

    # Limit candidate zones for CP-SAT tractability
    scored = df.copy()
    scored["zone_score"] = scored.apply(lambda r: _score_zone(r, weights), axis=1)
    candidates = scored.sort_values("zone_score", ascending=False).head(24).reset_index(drop=True)
    n = len(candidates)
    if n == 0:
        return {"solver": "ortools_cpsat", "assignments": [], "objective_estimate": 0.0}

    model = cp_model.CpModel()
    select = [model.NewBoolVar(f"z{i}") for i in range(n)]
    # scale scores to ints
    score_i = [int(round(float(candidates.loc[i, "zone_score"]) * 1000)) for i in range(n)]

    model.Add(sum(select) <= max_zones)
    model.Add(sum(select[i] * min_officers for i in range(n)) <= officers)
    model.Add(sum(select) <= vehicles)
    model.Maximize(sum(select[i] * score_i[i] for i in range(n)))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    assignments = []
    for i in range(n):
        if solver.Value(select[i]) == 1:
            row = candidates.loc[i]
            assignments.append(
                {
                    "station_code": row.get("station_code"),
                    "grid_cell_id": row.get("grid_cell_id"),
                    "district_code": row.get("district_code"),
                    "zone_score": float(row["zone_score"]),
                    "officers_assigned": min_officers,
                    "vehicles_assigned": 1,
                    "best_patrol_zone": row.get("grid_cell_id"),
                    "best_shift": _pick_shift(row),
                    "best_patrol_route": f"ROUTE-{row.get('station_code')}-{row.get('grid_cell_id')}",
                }
            )
    return {
        "solver": "ortools_cpsat",
        "assignments": assignments,
        "objective_estimate": float(solver.ObjectiveValue()) / 1000.0,
        "status": solver.StatusName(status),
    }


def optimize_resources(officers: int = 18, vehicles: int = 6) -> dict[str, Any]:
    cfg = load_yaml(ml_root() / "configs" / "resource_ortools.yaml")
    df = _load_cells()
    run_id = new_run_id("resource")

    result = _ortools_optimize(df, cfg, officers, vehicles)
    if result is None:
        result = _greedy_optimize(df, cfg, officers, vehicles)

    # Materialize decision table
    rows = []
    for a in result["assignments"]:
        rows.append({**a, "run_id": run_id, "feature_set_id": "resource_v1"})
    out_df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["best_patrol_zone", "best_shift", "best_patrol_route"])
    path = write_parquet(out_df, ml_root() / "datasets" / "engineered" / "resource_optimization" / f"{run_id}.parquet")
    write_parquet(out_df, ml_root() / "datasets" / "engineered" / "resource_optimization" / "latest.parquet")

    payload = {
        "run_id": run_id,
        "officers": officers,
        "vehicles": vehicles,
        **result,
        "output": str(path),
        "serves": ["/advisor", "/simulation"],
        "note": "Suggestions only — humans retain deployment authority",
    }
    write_json(ml_root() / "reports" / f"resource_{run_id}.json", payload)
    write_json(ml_root() / "artifacts" / "resource_ortools" / "latest_plan.json", payload)
    return payload
