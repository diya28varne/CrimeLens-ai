"""Executive intelligence mart (D5) — grounded context packs for /reports."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from crimelens_ml.utils import ml_root, new_run_id, write_json
from crimelens_ml.utils.io import read_parquet, write_parquet


def _ensure_risk() -> pd.DataFrame:
    path = ml_root() / "datasets" / "engineered" / "risk_intelligence" / "latest.parquet"
    if not path.exists():
        from crimelens_ml.synthetic import materialize_synthetic

        materialize_synthetic()
    return read_parquet(path)


def _ensure_hotspot() -> pd.DataFrame:
    path = ml_root() / "datasets" / "engineered" / "hotspot_evolution" / "latest.parquet"
    if not path.exists():
        from crimelens_ml.synthetic import materialize_synthetic

        materialize_synthetic()
    return read_parquet(path)


def _ensure_advisor() -> pd.DataFrame | None:
    path = ml_root() / "datasets" / "engineered" / "strategic_intelligence" / "latest.parquet"
    if path.exists():
        return read_parquet(path)
    return None


def build_executive_mart() -> dict[str, Any]:
    risk = _ensure_risk()
    hotspot = _ensure_hotspot()
    advisor = _ensure_advisor()

    risk = risk.copy()
    risk["as_of_ts"] = pd.to_datetime(risk["as_of_ts"], utc=True)
    as_of_naive = risk["as_of_ts"].dt.tz_convert("UTC").dt.tz_localize(None)
    risk["week"] = as_of_naive.dt.to_period("W-SUN").astype(str)
    risk["month"] = as_of_naive.dt.to_period("M").astype(str)

    rows: list[dict[str, Any]] = []
    context_packs: list[dict[str, Any]] = []

    for period_type, period_col in (("week", "week"), ("month", "month")):
        for (district, period), g in risk.groupby(["district_code", period_col]):
            total = int(g["CrimeFrequency7Days"].sum()) if "CrimeFrequency7Days" in g else len(g)
            # growth vs previous slice proxy
            mean_score = float(g["risk_score"].mean())
            prev_mask = risk["district_code"] == district
            growth = float(
                (g["risk_score"].mean() - risk.loc[prev_mask, "risk_score"].mean())
                / max(risk.loc[prev_mask, "risk_score"].mean(), 1e-3)
            )

            top_areas = (
                g.groupby("station_code")["risk_score"]
                .mean()
                .sort_values(ascending=False)
                .head(5)
                .reset_index()
                .rename(columns={"risk_score": "avg_risk"})
                .to_dict(orient="records")
            )

            offense_proxy = {
                "night_share": float(g["NightCrimeRatio"].mean()) if "NightCrimeRatio" in g else None,
                "festival_share": float(g["FestivalImpactScore"].mean()) if "FestivalImpactScore" in g else None,
                "high_crit_share": float(g["severity_high_crit_share_7d"].mean())
                if "severity_high_crit_share_7d" in g
                else None,
            }

            hot = hotspot[hotspot["district_code"] == district] if "district_code" in hotspot.columns else hotspot
            growing = int((hot.get("hotspot_growth") == "Growing").sum()) if len(hot) else 0

            actions: list[dict[str, Any]] = []
            if advisor is not None and len(advisor):
                ad = advisor[advisor["district_code"] == district]
                if len(ad):
                    vc = ad["recommended_action"].value_counts().head(5)
                    actions = [{"action": k, "count": int(v)} for k, v in vc.items()]

            resource = {
                "avg_patrol_coverage": float(g["PatrolCoverageIndex"].mean()) if "PatrolCoverageIndex" in g else None,
                "avg_cctv_coverage": float(g["CCTVCoverageIndex"].mean()) if "CCTVCoverageIndex" in g else None,
                "avg_response_score": float(g["EmergencyResponseScore"].mean())
                if "EmergencyResponseScore" in g
                else None,
            }

            row = {
                "period_type": period_type,
                "period_id": str(period),
                "district_code": district,
                "district_name": g["district_name"].iloc[0] if "district_name" in g.columns else district,
                "crime_total_proxy": total,
                "crime_growth_pct": round(growth * 100, 2),
                "avg_risk_score": round(mean_score, 4),
                "risk_band": _band(mean_score),
                "top_risk_areas_json": json.dumps(top_areas),
                "by_severity_proxy_json": json.dumps(offense_proxy),
                "growing_hotspots": growing,
                "recommended_actions_json": json.dumps(actions),
                "resource_usage_json": json.dumps(resource),
                "budget_usage_json": json.dumps({"budget_pressure": round(1 - float(np.mean(list(filter(None, [resource.get("avg_patrol_coverage"), 0.5])))), 3)}),
                "prediction_summary_json": json.dumps(
                    {
                        "avg_risk_score": mean_score,
                        "cells": int(g["grid_cell_id"].nunique()) if "grid_cell_id" in g else len(g),
                        "critical_share": float((g["risk_level"] == "Critical").mean())
                        if "risk_level" in g
                        else None,
                    }
                ),
                "feature_set_id": "executive_v1",
                "provenance": "engineered_mart",
            }
            rows.append(row)

            context_packs.append(
                {
                    "template_hints": ["weekly", "daily", "festival"] if period_type == "week" else ["weekly"],
                    "scope": {"district_code": district, "period_type": period_type, "period_id": str(period)},
                    "headline": {
                        "crime_growth_pct": row["crime_growth_pct"],
                        "risk_band": row["risk_band"],
                        "avg_risk_score": row["avg_risk_score"],
                    },
                    "hotspots": {"growing": growing, "top_areas": top_areas},
                    "predictions": json.loads(row["prediction_summary_json"]),
                    "recommended_actions": actions,
                    "resources": resource,
                    "citation_note": (
                        "All numbers from CrimeLens executive mart / offline ML artifacts — "
                        "LLM must not invent KPIs."
                    ),
                }
            )

    mart = pd.DataFrame(rows)
    run_id = new_run_id("exec_mart")
    out_dir = ml_root() / "datasets" / "engineered" / "executive_mart"
    parquet_path = write_parquet(mart, out_dir / f"{run_id}.parquet")
    write_parquet(mart, out_dir / "latest.parquet")
    packs_path = out_dir / "context_packs.json"
    write_json(packs_path, {"run_id": run_id, "packs": context_packs[:200], "n_packs": len(context_packs)})

    report = {
        "run_id": run_id,
        "n_rows": len(mart),
        "n_context_packs": len(context_packs),
        "parquet": str(parquet_path),
        "context_packs": str(packs_path),
        "serves": ["/reports"],
        "note": "Reports module should load context packs as grounded LLM inputs",
    }
    write_json(ml_root() / "reports" / f"executive_mart_{run_id}.json", report)
    return report


def _band(score: float) -> str:
    if score >= 0.75:
        return "Critical"
    if score >= 0.55:
        return "High"
    if score >= 0.35:
        return "Medium"
    return "Low"
