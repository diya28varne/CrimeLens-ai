# Phase A/B implementation status

**Date:** 2026-07-26  
**Status:** Complete (offline plane runnable)

## Delivered

| Area | Location |
|------|----------|
| Configs | `services/ml/configs/` |
| Dataset layers | `services/ml/datasets/{raw,processed,engineered,synthetic}/` |
| Schemas | `services/ml/schemas/` |
| Preprocessing | `crimelens_ml.preprocessing` |
| Feature engineering | `crimelens_ml.feature_engineering` |
| Synthetic world | `crimelens_ml.synthetic` |
| Risk training (XGBoost) | `crimelens_ml.training.train_risk_pipeline` |
| Hotspot (HDBSCAN→DBSCAN fallback) | `crimelens_ml.training.train_hotspot_pipeline` |
| Attributions (SHAP-compatible) | `crimelens_ml.explainability` via `pred_contribs` |
| Local registry | `crimelens_ml.registry` → `artifacts/<model>/CURRENT` |
| CLI | `crimelens-ml run-phase-ab` |

## Smoke result (local)

- Risk rows: 21,600 · Hotspot cells: 480
- Risk macro-F1 on synthetic holdout: ~0.97 (labels derived from engineered intensity — expect lower on real PostGIS extracts)
- Hotspot algorithm: DBSCAN fallback (install optional `crimelens-ml[hotspot]` for HDBSCAN)
- Growth macro-F1: deterministic from density deltas on synthetic

## Next (Phase C) — **done**

See [`PHASE_C_STATUS.md`](./PHASE_C_STATUS.md).

## Next (Phase D)

Story Transformer sequences, outcome-linked D7 audit workflow, live PostGIS extract jobs, drift monitoring.
