"""Local model registry — versioned artifacts + manifest (DB promotion later)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from crimelens_ml.utils import ml_root, new_run_id, write_json


def artifact_dir(model_code: str, version: str | None = None) -> Path:
    version = version or new_run_id("v")
    path = ml_root() / "artifacts" / model_code / version
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_model_bundle(
    model_code: str,
    model: Any,
    meta: dict[str, Any],
    version: str | None = None,
) -> dict[str, str]:
    folder = artifact_dir(model_code, version)
    model_path = folder / "model.joblib"
    meta_path = folder / "manifest.json"
    joblib.dump(model, model_path)
    meta = {**meta, "model_code": model_code, "artifact_dir": str(folder)}
    write_json(meta_path, meta)

    # current pointer
    current = ml_root() / "artifacts" / model_code / "CURRENT"
    current.write_text(folder.name, encoding="utf-8")
    pointer = {
        "model_code": model_code,
        "version": folder.name,
        "path": str(folder),
        "promotion": "local_current",
        "note": "Promote to Postgres model_registry via API/worker job in serving phase",
    }
    write_json(ml_root() / "artifacts" / model_code / "current_manifest.json", pointer)
    return {"version": folder.name, "dir": str(folder), "model": str(model_path)}


def load_current_model(model_code: str) -> tuple[Any, dict[str, Any]]:
    root = ml_root() / "artifacts" / model_code
    version = (root / "CURRENT").read_text(encoding="utf-8").strip()
    folder = root / version
    model = joblib.load(folder / "model.joblib")
    meta = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    return model, meta
