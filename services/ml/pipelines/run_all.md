# CrimeLens ML pipelines — Phase A/B

## Commands

From repo root (after `uv sync --all-packages`):

```bash
uv run --package crimelens-ml crimelens-ml synthesize
uv run --package crimelens-ml crimelens-ml train-risk
uv run --package crimelens-ml crimelens-ml train-hotspot
uv run --package crimelens-ml crimelens-ml run-phase-ab
```

## Flow

1. **synthesize** — domain world → `datasets/{raw,processed,engineered,synthetic}`
2. **train-risk** — XGBoost D1 → `artifacts/risk_xgb/` + SHAP audit + `reports/`
3. **train-hotspot** — HDBSCAN/DBSCAN D2 + growth classifier → `artifacts/hotspot_hdbscan/`

Serving into Postgres (`prediction_*`, `hotspot_*`, `explanation_artifacts`) is the next integration step (API/worker promotion job). Offline artifacts are already shaped for those tables.
