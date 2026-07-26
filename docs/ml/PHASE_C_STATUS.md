# Phase C implementation status

**Date:** 2026-07-26  
**Status:** Complete (offline decision + narrative plane)

## Delivered

| Capability | Module / command |
|------------|------------------|
| Strategic Intelligence dataset (D3) | `crimelens_ml.datasets_builders.advisor` |
| Advisor ranker (LightGBM → HistGBM fallback) | `crimelens-ml train-advisor` |
| Executive mart + LLM context packs (D5) | `crimelens-ml build-mart` |
| Resource optimization (OR-Tools → greedy) | `crimelens-ml optimize-resources` |
| Artifact promotion bundle | `crimelens-ml promote` |
| PostGIS extract readiness | `crimelens-ml extract-status` |
| One-shot | `make ml-phase-c` / `crimelens-ml run-phase-c` |

## Optional extras

```bash
uv sync --all-packages --extra advisor --extra optimize --extra hotspot --package crimelens-ml
# or from services/ml extras: lightgbm, ortools, hdbscan
```

Without extras, Phase C still runs using sklearn HistGradientBoosting and greedy coverage.

## Platform wiring

- Advisor scores → `/advisor` action ranking evidence  
- Context packs → `/reports` grounded LLM inputs (`citation_note` forbids invented KPIs)  
- Resource plans → `/advisor` + `/simulation` deployment suggestions  
- `artifacts/promotions/latest.json` → worker/API ingest into `model_registry` / `prediction_*` / `explanation_artifacts`

## Next (Phase D)

Story Transformer sequences, outcome-linked D7 audit workflow, live PostGIS extract jobs, drift monitoring.
