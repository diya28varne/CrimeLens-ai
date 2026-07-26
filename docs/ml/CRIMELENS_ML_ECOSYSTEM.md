# CrimeLens AI — Machine Learning Ecosystem Architecture

**Status:** Phase A/B implementation in progress under `services/ml` — architecture approved  
**Owner:** Lead ML Architect  
**Scope:** Offline prediction plane that powers Prediction, Simulation, Advisor, Story, Explain, and Reports  
**Non-goals:** Generic Kaggle-style notebooks, toy CSVs as the system of record, autonomous dispatch  

**Implementation entrypoint:**  
- Phase A/B: `uv run --package crimelens-ml crimelens-ml run-phase-ab`  
- Phase C: `uv run --package crimelens-ml crimelens-ml run-phase-c`  
**Feature catalog:** [`docs/ml/features/catalog.md`](./features/catalog.md)  
**Status:** [`PHASE_AB_STATUS.md`](./PHASE_AB_STATUS.md) · [`PHASE_C_STATUS.md`](./PHASE_C_STATUS.md)  

**Related docs:** [`docs/ai/ARCHITECTURE.md`](../ai/ARCHITECTURE.md) · [`docs/database/SCHEMA.md`](../database/SCHEMA.md) · [`docs/ml/model-governance.md`](./model-governance.md) · [`docs/product/mvp-scope.md`](../product/mvp-scope.md) · ADR-0001 / ADR-0002

---

## 0. Design principles (CrimeLens-specific)

1. **One platform, seven datasets, one spine.** All datasets share Karnataka jurisdiction keys (`district_id`, `station_id`, `grid_cell_id`), incident lineage, and model registry versions — not seven unrelated experiments.
2. **PostgreSQL + PostGIS is the system of record.** Parquet under `services/ml/datasets/` is an *offline feature store snapshot*, not a parallel truth.
3. **Plane separation (from AI Architecture).** Statistical ML scores + SHAP → DB tables. LLM agents / Advisor / Reports *read* those scores; they do not retrain in chat.
4. **Human-in-the-loop.** Outputs are decision support. Labels like `recommended_action` are policy suggestions with confidence + explanation, never orders.
5. **Reuse existing modules.** Training jobs write into `model_registry`, `prediction_runs`, `prediction_values`, `explanation_artifacts`, `hotspot_runs`, `hotspot_features` already designed in SCHEMA.md and consumed by `/prediction`, `/simulation`, `/advisor`, `/explain`, `/reports`.
6. **Expand `services/ml/`** (already in the monorepo) rather than inventing a separate `backend/ml/` root. Folder names below map 1:1 to your requested layout *inside* `services/ml/`.

---

## 1. Integration map — how ML powers every flagship feature

```text
                    ┌──────────────────────────────────────────────┐
                    │         services/ml (offline plane)          │
                    │  extract → engineer → train → score → SHAP   │
                    └────────────────────┬─────────────────────────┘
                                         │ writes
                                         ▼
              PostgreSQL: model_registry · prediction_* · hotspot_* · explanation_artifacts
                                         │
         ┌───────────┬───────────┬───────┴───────┬───────────┬──────────┐
         ▼           ▼           ▼               ▼           ▼          ▼
   /prediction  /simulation  /advisor       /story      /explain   /reports
   risk scores  twin overlay action ranks  sequences   Decision   LLM brief
   + map layer  hotspot grow  + resources   timeline    Cards      aggregates
```

| Dataset | Owner API module | Consuming UI | Primary DB sinks |
|---------|------------------|--------------|------------------|
| D1 Crime Risk Intelligence | `predictions` | `/prediction`, Map | `prediction_runs/values` (`metric=risk_score`) |
| D2 Smart Hotspot Evolution | `predictions` + `simulation` | `/map`, `/simulation` | `hotspot_runs/features`; twin overlays |
| D3 Strategic Intelligence | `advisor` | `/advisor` | `prediction_values.properties` + advisor evidence; optional `decision_*` |
| D4 Crime Story Playback | `story` | `/story` | Event sequences (derived views / JSON artifacts); not a flat classifier |
| D5 Executive Intelligence | `reports` | `/reports` | Aggregated marts → LLM report context |
| D6 Resource Optimization | `advisor` + `simulation` | `/advisor`, `/simulation` | Route/zone suggestions in properties + twin controls |
| D7 XAI Audit | `explain` | `/explain`, `/admin` | `explanation_artifacts` + audit trail |

---

## 2. Proposed folder structure (maps to monorepo)

Do **not** create a parallel `backend/` root. Expand the existing offline plane:

```text
services/ml/
├── pyproject.toml                 # crimelens-ml (Polars, XGBoost, LightGBM, SHAP, …)
├── configs/                       # YAML: features, models, horizons, grids
│   ├── risk_xgboost.yaml
│   ├── hotspot_hdbscan.yaml
│   ├── advisor_lightgbm.yaml
│   ├── story_transformer.yaml
│   ├── resource_ortools.yaml
│   └── common.yaml                # CRS, geohash precision, Karnataka bounds
├── datasets/                      # Feature store snapshots (gitignored data; keep .gitkeep)
│   ├── raw/                       # Extracts from PostGIS / approved external feeds
│   ├── processed/                 # Cleaned, typed, validated
│   ├── engineered/                # Model-ready matrices + feature manifests
│   └── synthetic/                 # Domain generator outputs (demo / CI)
├── schemas/                       # Pandera / JSON Schema contracts per dataset
├── src/crimelens_ml/
│   ├── preprocessing/
│   ├── feature_engineering/
│   ├── training/
│   ├── evaluation/
│   ├── explainability/
│   ├── models/                    # Thin wrappers (XGB, LGBM, HDBSCAN, …)
│   ├── synthetic/                 # Realistic incident/world generators
│   ├── registry/                  # Promote → model_registry / is_current
│   └── utils/                     # Geo, time, logging, IO
├── pipelines/                     # CLI entrypoints (features / train / score / explain)
├── notebooks/                     # Exploration only — production logic stays in src/
├── reports/                       # Eval HTML/MD artifacts per run
├── artifacts/                     # Model binaries + SHAP caches (gitignored)
└── tests/
```

| Requested path | CrimeLens location | Why |
|----------------|--------------------|-----|
| `backend/ml/...` | `services/ml/...` | Matches ADR-0001 modular monolith + existing folder map |
| Online inference API | `services/api` modules | AuthZ, jurisdiction, OpenAPI already live here |
| Shared types | `packages/py-domain` | No duplicated domain rules |

---

## PART 1 — Seven datasets (full contracts)

### Shared keys (every dataset)

| Column | Why it exists |
|--------|----------------|
| `district_id` / `district_code` | Jurisdiction AuthZ + socio-economic join |
| `station_id` / `station_code` | Operational grain for patrol & twin |
| `grid_cell_id` / `geohash` | Spatial aggregation without raw PII coordinates in training matrices |
| `as_of_ts` | Point-in-time correctness (no leakage) |
| `horizon_hours` | Forecast horizon alignment with `prediction_runs` |
| `model_feature_set_id` | Ties row to feature manifest / version |

**Storage format (all):** Apache Parquet (columnar, typed) under `datasets/{raw,processed,engineered}/`, plus optional DuckDB catalog for local joins. **Promotion path:** score job → PostgreSQL prediction/hotspot/explanation tables.

---

### DATASET 1 — Crime Risk Intelligence Dataset

| Field | Value |
|-------|--------|
| **Purpose** | Predict future crime **risk_level** for a spatial-temporal unit |
| **Owner module** | `services/api/app/modules/predictions` → UI `/prediction`, Map risk layer |
| **Grain** | One row = `(grid_cell_id OR station_id) × as_of_ts × horizon_hours` |
| **Target** | `risk_level` ∈ `{Low, Medium, High, Critical}` (ordinal; also train `risk_score` ∈ [0,1] for ranking) |
| **Recommended algorithm** | **XGBoost** (multi-class / ordinal via custom objective or two-stage: regress score → calibrate bands) |
| **Evaluation** | Macro-F1, weighted-F1, PR-AUC (Critical/High), calibration (ECE), temporal backtest |
| **Storage** | `datasets/engineered/risk_intelligence/v{N}/` Parquet + `schemas/risk_intelligence.json` |

#### Column groups (why each exists)

**Location features**

| Column | Why |
|--------|-----|
| `centroid_lat`, `centroid_lon` | Spatial context for twin/map (validated WGS84) |
| `geohash_7` | Stable cell id; privacy-preserving aggregation |
| `district_urban_flag` | Urban vs rural baseline risk differs |
| `distance_to_highway_m` | Transit corridors elevate property/theft risk |
| `distance_to_commercial_hub_m` | Crowding / opportunity crimes |
| `road_density_km_per_km2` | Accessibility for offenders and patrol |

**Time features**

| Column | Why |
|--------|-----|
| `hour_sin`, `hour_cos` | Cyclical hour encoding |
| `dow`, `is_weekend` | Weekend vs weekday patterns |
| `is_night` | Night-time violence / burglary regimes |
| `is_pay_week`, `is_festival_window` | Cash/festival spikes (Karnataka calendar) |
| `month`, `season` | Seasonality |

**Crime features**

| Column | Why |
|--------|-----|
| `incidents_1d/7d/30d` | Short/medium momentum |
| `severity_high_crit_share_7d` | Mix quality, not just volume |
| `top_offense_share_30d` | Concentration of offense type |
| `repeat_location_flag` | Same-cell recurrence |

**Weather features**

| Column | Why |
|--------|-----|
| `temp_c`, `precip_mm`, `visibility_km` | Outdoor opportunity / street crime modulation |
| `extreme_weather_flag` | Suppresses or shifts activity |

**Infrastructure features**

| Column | Why |
|--------|-----|
| `cctv_density_per_km2` | Deterrence / detection coverage |
| `streetlight_coverage_pct` | Night risk |
| `open_space_pct` | Guardianship / loitering |

**Socio-economic features** (join `socio_economic_indicators`)

| Column | Why |
|--------|-----|
| `unemployment_rate`, `poverty_index`, `literacy_rate`, `urban_pct`, `population_density` | Already used in Analytics correlations; reuse for risk |

**Law-enforcement features**

| Column | Why |
|--------|-----|
| `patrol_hours_7d`, `officers_on_duty_avg` | Guardianship supply |
| `avg_response_minutes_30d` | Capability signal |
| `open_case_backlog` | Investigative load |

**Behaviour / network features**

| Column | Why |
|--------|-----|
| `repeat_offender_activity_score` | From network module entities |
| `link_density_local` | Local network intensity |

**Historical features**

| Column | Why |
|--------|-----|
| `risk_score_lag_7d`, `risk_score_lag_30d` | Autocorrelation |
| `days_since_last_critical` | Recency of severe events |
| `hotspot_persistence_days` | From D2 feedback loop |

**Output features (training labels / serving)**

| Column | Why |
|--------|-----|
| `risk_level` | Classification target |
| `risk_score` | Continuous score for map + twin |
| `label_source` | `observed_future_window` vs `weak_label` for audit |

**Relationships:** `incidents` → aggregate to cell; `socio_economic_indicators` → district; `hotspot_features` → persistence; `persons/network` → behaviour scores.

**Preprocessing / engineering:** see Parts 2–3. Leakage rule: features use only data `< as_of_ts`; label from `(as_of_ts, as_of_ts+horizon]`.

---

### DATASET 2 — Smart Hotspot Evolution Dataset

| Field | Value |
|-------|--------|
| **Purpose** | Detect hotspots and classify **evolution** for Digital Twin + heatmap |
| **Owner module** | `predictions` (hotspot runs) + `simulation` (growth overlays) |
| **Grain** | Grid cell (or HDBSCAN cluster id) × time window |
| **Target** | `hotspot_growth` ∈ `{Growing, Stable, Shrinking}` |
| **Algorithms** | **HDBSCAN** (primary density clusters) + **DBSCAN** (baseline); growth classifier = Gradient Boosting on cluster/cell deltas *or* rule+ML hybrid |
| **Evaluation** | Silhouette / DBI / CHI on spatial clusters; F1 on growth labels; stability across adjacent windows |
| **Storage** | `datasets/engineered/hotspot_evolution/` + write `hotspot_runs` / `hotspot_features` |

#### Column groups

| Column | Why |
|--------|-----|
| `grid_x`, `grid_y`, `cell_area_m2` | Regular lattice for twin/heatmap |
| `incident_density`, `kde_intensity` | Core spatial signal |
| `traffic_index`, `population_flow_index` | Ambient exposure |
| `lighting_index`, `road_connectivity_score` | Environmental criminology |
| `cctv_density`, `patrol_density` | Guardianship |
| `historical_density_30d/90d` | Baseline vs spike |
| `dist_market_m`, `dist_school_m` | Attractors / soft targets |
| `festival_impact`, `weather_impact` | Transient shocks |
| `cluster_id`, `cluster_core_distance` | HDBSCAN outputs as features for growth stage |
| `density_delta_7d`, `density_delta_30d` | Evolution signal → `hotspot_growth` |

**Relationships:** Feeds Simulation scenario multipliers; Prediction hotspot GeoJSON; Advisor “risk areas.”

---

### DATASET 3 — Strategic Intelligence Dataset

| Field | Value |
|-------|--------|
| **Purpose** | Rank / select **recommended_action** for Advisor |
| **Owner module** | `advisor` (consumes scores as evidence; optional dedicated ranker) |
| **Grain** | Station or district × as_of_ts × candidate action |
| **Target** | `recommended_action` ∈ Increase Patrol, Deploy CCTV, Deploy Drone, Traffic Diversion, Community Awareness, Emergency Response, Investigation Priority, No Action |
| **Algorithms** | **LightGBM** (primary ranking/multiclass) + **CatBoost** (categorical-heavy alternative / ensemble) |
| **Evaluation** | Top-1 / Top-3 accuracy vs expert/heuristic labels; cost-sensitive utility; pairwise ranking NDCG if listwise training |
| **Storage** | `datasets/engineered/strategic_intelligence/` |

#### Column groups

| Column | Why |
|--------|-----|
| `risk_score`, `hotspot_growth`, `high_crit_share` | Demand side (from D1/D2) |
| `officers_available`, `vehicles_available` | Supply constraints |
| `budget_remaining_inr`, `cctv_slots_open`, `drone_available` | Feasibility |
| `avg_response_minutes`, `clearance_rate_30d` | Performance baselines |
| `action_success_rate_hist` | Historical effectiveness of *this* action in similar contexts |
| `estimated_cost`, `estimated_eta_hours` | Trade-offs for Advisor narrative |
| `policy_constraint_flags` | Hard blocks (e.g. no drone near airport) |

**Relationships:** Advisor brief `ActionOut` ranks by model score; Explain justifies; Reports summarize recommended actions; Simulation can apply action as control.

**Labeling strategy (enterprise):** Start with **policy heuristics + officer-reviewed weak labels**, then promote to curated training set — never invent “ground truth” from random assignment.

---

### DATASET 4 — Crime Story Playback Dataset

| Field | Value |
|-------|--------|
| **Purpose** | Temporal replay / sequence modelling for `/story` |
| **Owner module** | `story` |
| **Grain** | **Event** in a case/incident timeline (NOT one-row-per-case classification) |
| **Target** | Sequence tasks: next-event type, time-to-next-milestone, anomaly in timeline — not a single class label |
| **Algorithm recommendation** | **Transformer encoder (primary)** over LSTM |

#### Why Transformer over LSTM

| Criterion | LSTM | Transformer (recommended) |
|-----------|------|------------------------------|
| Variable-length case timelines | OK | Better with masking |
| Long-range deps (FIR → evidence → arrest) | Weakens | Attention handles |
| Irregular time gaps | Needs hacks | Time embeddings / RoPE-style deltas |
| Explainability for Story UI | Hidden states opaque | Attention → “which prior events mattered” |
| Datathon/pilot scale | Fine | Fine with small encoder |

**LSTM reserved for:** tiny onboard/edge or ultra-low-data ablation baselines.

#### Event schema (sequential)

| Column | Why |
|--------|-----|
| `case_id` / `incident_id` | Sequence key |
| `event_id`, `event_ts`, `event_type` | Ordered playback |
| `actor_type` (`officer`/`suspect`/`system`/`witness`) | Role in narrative |
| `action_code` | Officer/suspect action vocabulary |
| `evidence_stage`, `case_status` | Progress |
| `response_minutes_cum` | Response timeline |
| `arrest_flag`, `chargesheet_flag` | Outcome markers |
| `weather_code`, `nearby_event_code` | Context |
| `geo_delta_m`, `geohash` | Movement between events |
| `delta_t_hours` | Irregular sampling |

**Storage:** Parquet partitioned by `district_id` + `case_id` lists; optional JSONL for LLM story narration context.

**Relationships:** Story UI timeline; Explain “similar cases”; Advisor pattern cards.

---

### DATASET 5 — Executive Intelligence Dataset

| Field | Value |
|-------|--------|
| **Purpose** | Structured mart for **LLM report generation** (`/reports`) |
| **Owner module** | `reports` |
| **Grain** | `period_type` (`week`/`month`) × `district_id` (and state rollup) |
| **Target** | **None** (not a classifier) |
| **“Model”** | Deterministic aggregations + optional forecast *summaries* from D1/D2; LLM narrates with citations |
| **Evaluation** | Schema validation, freshness SLA, citation coverage, factuality checklist (no classic ML metrics) |
| **Storage** | `datasets/engineered/executive_mart/` + DB materialized views |

#### Columns (feed LLM context packs)

| Column | Why |
|--------|-----|
| `period_start`, `period_end`, `district_name` | Report scope |
| `crime_total`, `crime_growth_pct` | Headline KPIs |
| `by_offense_json`, `by_severity_json` | Breakdowns |
| `top_risk_areas_json` | From D1/D2 |
| `prediction_summary_json` | Horizon forecasts |
| `recommended_actions_json` | From D3 |
| `resource_usage_json`, `budget_usage_json` | Ops finance narrative |
| `anomaly_findings_json` | From Analytics insights |
| `source_run_ids` | Audit / citation to prediction & hotspot runs |

**LLM pipeline:** Reports module builds a **grounded context pack** from this mart → Gemini/agent synthesizes briefing → Present mode. Numbers always come from the mart, never from the LLM’s memory.

---

### DATASET 6 — Police Resource Optimization Dataset

| Field | Value |
|-------|--------|
| **Purpose** | Optimize deployment: zone, route, shift |
| **Owner module** | `advisor` + `simulation` |
| **Grain** | Decision instance: station × shift_window |
| **Targets** | `best_patrol_zone`, `best_patrol_route_id`, `best_shift` (multi-head or cascaded decisions) |
| **Algorithm recommendation** | **OR-Tools (primary)** + graph shortest-path; RL optional later |

#### Why OR-Tools / graphs over RL (now)

| Approach | Fit | Verdict |
|----------|-----|---------|
| **Graph + OR-Tools CP-SAT / routing** | Hard constraints (officers, vehicles, max hours, coverage), interpretable | **Primary for enterprise pilot** |
| Classic graph (Dijkstra / betweenness on road network) | Travel time, corridor choice | Use inside OR-Tools cost matrix |
| **Reinforcement learning** | Long-horizon adaptive patrol | **P2+** — needs sim fidelity, reward design, safety constraints; hard to audit for police governance |

#### Columns

| Column | Why |
|--------|-----|
| `officers_available`, `vehicles_available` | Capacity |
| `road_edge_id`, `travel_time_min`, `traffic_index` | Network costs |
| `crime_density`, `hotspot_score` | Demand |
| `event_load`, `festival_flag` | Temporary demand |
| `shift_code`, `fatigue_index` | Shift feasibility |
| `coverage_gap_score` | Objective component |

**Relationships:** Advisor actions (“Increase Patrol” + where); Twin controls; Reports resource usage.

---

### DATASET 7 — Explainable AI Audit Dataset

| Field | Value |
|-------|--------|
| **Purpose** | Persist explanations for governance, `/explain`, Admin audit |
| **Owner module** | `explain` (+ `model_governance`) |
| **Grain** | One explanation per `prediction_value_id` (or advisor action id) |
| **Target** | None for training; **outcome labels** filled later for monitoring |
| **Algorithm** | SHAP (TreeExplainer for XGB/LGBM); optional counterfactuals |
| **Evaluation** | Completeness (top-k features present), stability, reviewer acceptance rate |
| **Storage** | DB `explanation_artifacts` + Parquet archive `datasets/processed/xai_audit/` |

#### Columns

| Column | Why |
|--------|-----|
| `prediction_id`, `predicted_label`, `predicted_score` | What was said |
| `confidence` | Calibration / UI badge |
| `top_features_json`, `feature_importance_json` | Global/local |
| `shap_values_json` | Full local attribution |
| `model_code`, `model_version` | Reproducibility |
| `prediction_ts` | Temporal audit |
| `actual_outcome`, `outcome_observed_at` | Drift / accuracy monitoring |
| `audit_status` (`pending`/`reviewed`/`disputed`) | Governance |
| `reviewer_id`, `reviewer_notes` | Human oversight |
| `nl_explanation` | Officer-facing text (templated + LLM polish grounded on SHAP) |

---

## PART 2 — Feature engineering (enterprise catalog)

Shared module: `crimelens_ml.feature_engineering` producing a **feature manifest** (name, dtype, formula_id, owners, leakage_safe).

| Feature | Formula / calculation | Why it helps | Used by |
|---------|----------------------|--------------|---------|
| `CrimeFrequency7Days` | count(incidents in cell, last 7d) | Short-term pressure | D1, D2, D3, D6 |
| `CrimeFrequency30Days` | count last 30d | Baseline volume | D1–D3, D5, D6 |
| `WeekendCrimeRatio` | weekend_cnt / max(total,1) over 30d | Temporal regime | D1, D3 |
| `NightCrimeRatio` | night_cnt / max(total,1) | Night ops planning | D1, D3, D6 |
| `FestivalImpactScore` | weighted sum of festival proximity windows × historical lift | Spike anticipation | D1–D3, D6 |
| `CommercialRiskScore` | f(dist_market, footfall, offense mix) | Opportunity crime | D1, D2 |
| `PatrolCoverageIndex` | patrol_hours / (cell_area × demand) | Guardianship gap | D1, D3, D6 |
| `CCTVCoverageIndex` | cctv_count / area normalized | Deterrence | D1–D3 |
| `EmergencyResponseScore` | inverse of avg response minutes (clipped) | Capability | D3, D6 |
| `WeatherRiskIndex` | weighted precip/visibility/temp anomalies | Context | D1, D2, D4 |
| `MobilityScore` | traffic × population_flow | Exposure | D2, D6 |
| `RoadAccessibilityScore` | connectivity / travel impedance | Escape & patrol access | D2, D6 |
| `HistoricalSimilarityScore` | distance in feature space to past high-risk windows | Analogical reasoning for Explain/Story | D1, D4, D7 |
| `RepeatOffenderScore` | network module activity in catchment | Recidivism pressure | D1, D3, D4 |
| `HotspotPersistenceScore` | days cell in hotspot core | Chronic vs acute | D1, D2, D5 |
| `SocioEconomicRiskIndex` | standardized blend of unemployment, poverty, density, literacy (signed) | Structural context (Analytics-aligned) | D1, D3, D5 |

**Rules:** All rolling features are point-in-time; manifests versioned (`feature_set=risk_v3`); engineered Parquet includes `feature_set_id`.

---

## PART 3 — Preprocessing pipeline

Module: `crimelens_ml.preprocessing`

| Stage | Strategy |
|-------|----------|
| **Missing values** | Numeric: median within district+month; categorical: `"unknown"`; socio: district carry-forward; **never** impute target |
| **Outliers** | Winsorize continuous at 1–99% within district; spatial density caps; flag `is_outlier` for audit |
| **Categorical encoding** | Tree models: native category / ordinal codes; linear ablations: target encoding with CV |
| **Scaling** | Trees: optional; distance/OR-Tools costs: min-max or robust scale per district |
| **Spatial** | Validate lon/lat in Karnataka bbox; snap to station jurisdiction; drop null geography |
| **Temporal** | UTC→Asia/Kolkata for local hour; cyclical encodings; festival calendar join |
| **Weather** | Align nearest station-hour; interpolate ≤3h gaps; else mark missing |
| **GeoHash** | Precision 7 default (~153m); store both geohash and grid_id |
| **Coordinate validation** | WGS84; reject (0,0); AuthZ: training extract already jurisdiction-scoped |
| **Class balancing** | Risk: class weights + focal loss option; **no** indiscriminate SMOTE on spatial data (breaks dependence) — prefer weighted sampling by cell |
| **Data validation** | Pandera schemas per dataset; fail pipeline on contract break; log quarantine rows |

---

## PART 4 — Training pipelines (three primary)

Each pipeline CLI under `services/ml/pipelines/`:

### 4.1 Crime Risk Prediction (`train_risk`)

1. **Load** engineered risk Parquet + schema validate  
2. **Validate** temporal split (train < val < test by `as_of_ts`)  
3. **Feature select** via manifest  
4. **Train** XGBoost (`risk_xgboost.yaml`)  
5. **Evaluate** Part 5 metrics → `reports/risk/{run_id}.md`  
6. **Save** `artifacts/risk/{version}/model.json` + calibrator  
7. **Version** register `model_registry` (`model_code=risk_xgb`)  
8. **Log** MLflow-compatible or structured JSON logs (params, metrics, git sha)  
9. **Score** batch → `prediction_runs` / `prediction_values` (`is_current` pointer)

### 4.2 Hotspot Detection (`train_hotspot`)

1. Load spatial window extracts  
2. HDBSCAN fit (min_cluster_size from config)  
3. Derive growth labels from density deltas  
4. Optional secondary classifier for `hotspot_growth`  
5. Write `hotspot_runs` / `hotspot_features`  
6. Version + silhouette report  

### 4.3 Strategic Advisor (`train_advisor`)

1. Load D3 with constraints  
2. LightGBM multiclass / LambdaMART  
3. CatBoost challenger  
4. Promote winner by utility metric + constraint violation rate  
5. Export action priors for Advisor service (read-only scores)

**Logging:** run_id, config hash, feature_set_id, data_interval, metrics, artifact URI — aligned with `docs/ml/model-governance.md`.

---

## PART 5 — Evaluation modules

| Task | Metrics | Why appropriate |
|------|---------|-----------------|
| Risk classification | Precision/Recall/F1 (macro + Critical) | Imbalanced severity; Critical misses costly |
| Risk ranking | ROC-AUC / PR-AUC | Threshold-free ranking for maps |
| Calibration | ECE / reliability diagram | Officers interpret “confidence” |
| Hotspot clustering | Silhouette, Davies–Bouldin, Calinski–Harabasz | Internal cluster quality without labels |
| Hotspot growth | F1 per class | Evolution is supervised second stage |
| Advisor actions | Top-k accuracy, constraint-feasible rate | Wrong but infeasible action is worse than abstain |
| Regression heads (`risk_score`) | RMSE, MAE | Continuous map intensity |
| Story sequences | Next-event accuracy, MAE on Δt | Sequential fidelity |
| Reports mart | Schema pass rate, freshness | Not ML accuracy — data product SLA |

Module: `crimelens_ml.evaluation` with shared temporal cross-validation helpers.

---

## PART 6 — Explainability pipeline

Module: `crimelens_ml.explainability` → API `explain` Decision Cards

| Capability | Implementation |
|------------|----------------|
| **SHAP** | TreeExplainer for XGB/LGBM; store `shap_local` / `shap_global` |
| **Feature importance** | Gain + SHAP mean \|value\| |
| **Prediction confidence** | Calibrated probability / margin |
| **Decision explanation** | Template: top-3 positive/negative contributors with friendly labels (existing `explain/labels.py`) |
| **Historical similarity** | k-NN in engineered space among past High/Critical cells |
| **NL explanation** | Grounded sentence builder; optional LLM polish **citing SHAP factors only** |
| **Recommendation justification** | Join D3 action score + binding constraints (“CCTV slots=0 → not recommended”) |

Every scored prediction used in UI **must** have a D7 audit row (governance gate).

---

## PART 7 — Synthetic data generation

Module: `crimelens_ml.synthetic`

**Not** i.i.d. random rows. A **domain world model**:

1. **Spatial prior:** Karnataka districts/stations from seed org geometry; intensity maps from historical densities  
2. **Temporal prior:** hour-of-day / DOW / festival calendar multipliers  
3. **Weather prior:** seasonal precip/temp correlated with region  
4. **Crime generative process:** offense mix by urbanicity; clustered via Matérn / Neyman–Scott around hotspots  
5. **Patrol process:** coverage depletes local intensity (feedback for twin realism)  
6. **Resource process:** officer/vehicle availability with shift constraints  
7. **Story process:** stateful case Markov/Transformer-friendly event chains (FIR → visit → evidence → arrest/close)

Outputs land in `datasets/synthetic/` with `provenance=synthetic` and **never** silently mix into production `is_current` without a flag. Use for CI, demos, and cold-start feature tests.

---

## PART 8 — Documentation deliverables (on implementation)

| Doc | Content |
|-----|---------|
| This file | Ecosystem architecture (source of truth for plan) |
| `docs/ml/datasets/*.md` | One page per dataset (columns, joins, leakage) |
| `docs/ml/features/catalog.md` | Engineered feature dictionary |
| `docs/ml/pipelines/*.md` | Runbooks for train/score/explain |
| `configs/*.yaml` comments | Executable documentation |
| `reports/` templates | Eval report format |
| Update `model-governance.md` | Promotion gates tied to D7 completeness |

---

## Implementation plan (phased — after approval)

### Phase A — Foundation (no model weights yet)
1. Expand `services/ml` folders + configs + Pandera schemas  
2. PostGIS → Parquet extractors (incidents, socio, stations)  
3. Preprocessing + feature engineering for D1/D2 core features  
4. Synthetic generator v1 for CI  

### Phase B — Core predictors
5. Train risk XGBoost → register → score into `prediction_*`  
6. HDBSCAN hotspot pipeline → `hotspot_*`  
7. SHAP batch → `explanation_artifacts` → wire `/explain` to real artifacts  

### Phase C — Decision & narrative
8. Advisor LightGBM action ranker (heuristic labels → reviewed)  
9. Executive mart builder for `/reports`  
10. OR-Tools patrol sketch behind Advisor/Simulation flags  

### Phase D — Sequences & governance
11. Story event extract + small Transformer next-event (optional if data volume allows)  
12. D7 audit workflow + Admin review UI hooks  
13. Monitoring: outcome backfill, drift alerts  

**Explicitly deferred:** live weather APIs, full RL patrol agents, multi-city federation.

---

## Approval checklist

Please confirm or adjust before any Python training code is written:

- [ ] Agree `services/ml/` (not a new `backend/ml` root)  
- [ ] Agree D1 XGBoost + D2 HDBSCAN + D3 LightGBM/CatBoost + D6 OR-Tools-first + D4 Transformer-first  
- [ ] Agree Parquet feature store + PostgreSQL serving  
- [ ] Agree synthetic data is separate provenance  
- [ ] Agree Phase A→D order (or request a narrower first slice, e.g. **Phase A+B only**)

---

## Summary diagram (single backbone)

```text
Incidents + Socio + Org + Network (PostGIS)
        │
        ▼
   Extract (raw) → Preprocess → Feature Engineer
        │
        ├─► D1 Risk (XGBoost) ──────────────► prediction_values (risk)
        ├─► D2 Hotspot (HDBSCAN) ───────────► hotspot_features
        ├─► D3 Advisor (LightGBM/CatBoost) ─► action scores → /advisor
        ├─► D4 Story sequences (Transformer)► /story timelines
        ├─► D5 Executive mart ──────────────► /reports LLM context
        ├─► D6 Resources (OR-Tools) ────────► patrol suggestions
        └─► D7 SHAP audit ──────────────────► /explain + Admin
```

**End of architecture plan. No training/pipeline code has been implemented pending your approval.**
