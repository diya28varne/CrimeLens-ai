"""Strategic Intelligence dataset (D3) — heuristic labels for Advisor training."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from crimelens_ml.utils import ml_root, new_run_id
from crimelens_ml.utils.io import read_parquet, write_parquet

ACTIONS = [
    "Increase Patrol",
    "Deploy CCTV",
    "Deploy Drone",
    "Traffic Diversion",
    "Community Awareness",
    "Emergency Response",
    "Investigation Priority",
    "No Action",
]


def _recommend_action(row: pd.Series, rng: np.random.Generator) -> str:
    """Policy-style weak label — reviewed later by officers; not random."""
    risk = float(row.get("risk_score", 0))
    patrol = float(row.get("PatrolCoverageIndex", 0.5))
    cctv = float(row.get("CCTVCoverageIndex", 0.5))
    night = float(row.get("NightCrimeRatio", 0.3))
    festival = float(row.get("FestivalImpactScore", 0))
    resp = float(row.get("EmergencyResponseScore", 0.5))
    repeat = float(row.get("RepeatOffenderScore", 0.2))
    officers = float(row.get("officers_available", 8))
    slots = float(row.get("cctv_slots_open", 1))
    drone = float(row.get("drone_available", 0))

    if risk < 0.35 and patrol > 0.55:
        return "No Action"
    if risk >= 0.75 and resp < 0.45:
        return "Emergency Response"
    if risk >= 0.65 and repeat > 0.55:
        return "Investigation Priority"
    if festival > 0.4 and night > 0.4:
        return "Traffic Diversion" if rng.random() < 0.45 else "Community Awareness"
    if cctv < 0.35 and slots >= 1 and risk >= 0.5:
        return "Deploy CCTV"
    if risk >= 0.6 and drone >= 1 and patrol < 0.4:
        return "Deploy Drone"
    if patrol < 0.45 and officers >= 4 and risk >= 0.45:
        return "Increase Patrol"
    if risk >= 0.55:
        return "Community Awareness"
    return "No Action"


def build_advisor_frame(risk_df: pd.DataFrame | None = None, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    if risk_df is None:
        path = ml_root() / "datasets" / "engineered" / "risk_intelligence" / "latest.parquet"
        if not path.exists():
            from crimelens_ml.synthetic import materialize_synthetic

            materialize_synthetic()
        risk_df = read_parquet(ml_root() / "datasets" / "engineered" / "risk_intelligence" / "latest.parquet")

    # Station-day grain: take one row per station per day (first cell)
    snap = (
        risk_df.sort_values(["as_of_ts", "station_code", "grid_cell_id"])
        .groupby(["as_of_ts", "district_code", "station_code"], as_index=False)
        .first()
    )

    out = snap.copy()
    n = len(out)
    out["officers_available"] = np.clip(rng.normal(10 - 4 * out["risk_score"], 2.5), 2, 24).round()
    out["vehicles_available"] = np.clip(out["officers_available"] // 3 + rng.integers(0, 2, n), 1, 8)
    out["budget_remaining_norm"] = np.clip(rng.uniform(0.2, 1.0, n) - 0.25 * out["risk_score"], 0.05, 1)
    out["cctv_slots_open"] = rng.integers(0, 4, n)
    out["drone_available"] = rng.integers(0, 2, n)
    out["action_success_rate_hist"] = np.clip(0.4 + 0.35 * out["EmergencyResponseScore"] + rng.normal(0, 0.05, n), 0.1, 0.95)
    out["clearance_rate_30d"] = np.clip(0.35 + 0.4 * out["EmergencyResponseScore"] + rng.normal(0, 0.05, n), 0.1, 0.9)
    out["avg_response_minutes"] = out.get("avg_response_minutes", pd.Series(25, index=out.index))

    out["recommended_action"] = [_recommend_action(out.iloc[i], rng) for i in range(n)]
    out["label_source"] = "policy_heuristic_v1"
    out["feature_set_id"] = "advisor_v1"
    return out.reset_index(drop=True)


def materialize_advisor_dataset(seed: int = 42) -> dict[str, Any]:
    frame = build_advisor_frame(seed=seed)
    run_id = new_run_id("advisor_data")
    path = write_parquet(frame, ml_root() / "datasets" / "engineered" / "strategic_intelligence" / f"{run_id}.parquet")
    write_parquet(frame, ml_root() / "datasets" / "engineered" / "strategic_intelligence" / "latest.parquet")
    return {"run_id": run_id, "path": str(path), "n_rows": len(frame), "actions": ACTIONS}
