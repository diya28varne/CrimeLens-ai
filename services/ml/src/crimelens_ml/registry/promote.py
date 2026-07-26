"""Promote local ML artifacts into API-shaped payloads for model_registry / predictions / explanations.

Does not require a live DB — writes JSON manifests the worker/API can ingest.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crimelens_ml.utils import ml_root, new_run_id, write_json


def _read_current(model_code: str) -> dict[str, Any] | None:
    path = ml_root() / "artifacts" / model_code / "current_manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_manifest(model_code: str, version: str) -> dict[str, Any]:
    path = ml_root() / "artifacts" / model_code / version / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_promotion_bundle() -> dict[str, Any]:
    """Assemble promotion documents for risk, hotspot, advisor (+ optional SHAP)."""
    run_id = new_run_id("promote")
    now = datetime.now(UTC).isoformat()
    models = []

    for code, task, metric in (
        ("risk_xgb", "risk", "risk_score"),
        ("hotspot_hdbscan", "hotspot", "hotspot_intensity"),
        ("advisor_lgbm", "decision", "action_rank"),
    ):
        cur = _read_current(code)
        if not cur:
            continue
        meta = _read_manifest(code, cur["version"])
        models.append(
            {
                "model_registry": {
                    "model_code": code,
                    "model_version": cur["version"],
                    "task": task,
                    "framework": meta.get("algorithm") or meta.get("test_metrics") and "xgboost" or "unknown",
                    "is_active_candidate": True,
                    "metrics": {
                        k: meta[k]
                        for k in ("test_macro_f1", "val_macro_f1", "top3_accuracy", "growth_macro_f1")
                        if k in meta
                    },
                    "feature_set_id": meta.get("feature_set_id"),
                    "created_at": now,
                },
                "prediction_run_template": {
                    "model_code": code,
                    "model_version": cur["version"],
                    "task": task,
                    "metric": metric,
                    "scope_type": "station" if code != "hotspot_hdbscan" else "grid_cell",
                    "status": "ready_to_ingest",
                    "is_current": False,
                    "note": "Worker sets is_current after successful bulk insert",
                },
                "artifact_dir": cur.get("path"),
            }
        )

        shap_path = Path(cur["path"]) / "shap_audit.json" if cur.get("path") else None
        if shap_path and shap_path.exists():
            models[-1]["explanation_artifact_template"] = {
                "model_version": cur["version"],
                "source": str(shap_path),
                "format": "shap_compatible_json",
                "audit_status": "pending_review",
            }

    # Attach mart + resource plan pointers
    extras = {
        "executive_mart": str(ml_root() / "datasets" / "engineered" / "executive_mart" / "latest.parquet"),
        "context_packs": str(ml_root() / "datasets" / "engineered" / "executive_mart" / "context_packs.json"),
        "resource_plan": str(ml_root() / "artifacts" / "resource_ortools" / "latest_plan.json"),
    }

    bundle = {
        "promotion_run_id": run_id,
        "created_at": now,
        "models": models,
        "extras": extras,
        "ingest_contract": {
            "api_tables": [
                "model_registry",
                "prediction_runs",
                "prediction_values",
                "explanation_artifacts",
                "hotspot_runs",
                "hotspot_features",
            ],
            "authz_note": "Serving remains AuthZ-scoped in FastAPI; offline jobs must not bypass jurisdiction filters",
        },
    }
    out = ml_root() / "artifacts" / "promotions" / f"{run_id}.json"
    write_json(out, bundle)
    write_json(ml_root() / "artifacts" / "promotions" / "latest.json", bundle)
    return {"path": str(out), "n_models": len(models), "promotion_run_id": run_id}
