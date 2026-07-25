# CrimeLens AI — PostgreSQL / PostGIS / pgvector Database Design

**Status:** Design specification (no backend code, no Alembic implementation)  
**Engine:** PostgreSQL 16+  
**Extensions:** `postgis`, `postgis_raster` (optional later), `vector` (pgvector), `pgcrypto` (optional), `btree_gist` (optional)  
**CRS:** WGS84 — SRID **4326**  
**Time:** All timestamps stored as `timestamptz` (UTC)  
**Naming:** `snake_case`, plural table names, `*_id` FK columns  

---

## 1. Design Principles

1. **PostgreSQL is the system of record** for identity, org, incidents, predictions, audit, AI traces.  
2. **PostGIS** owns all spatial truth (points, polygons, distance, containment).  
3. **pgvector** stores embeddings for RAG (Qdrant deferred).  
4. **3NF for transactional entities**; controlled denormalization only in analytics materializations.  
5. **Jurisdiction safety** is data-modeled (`user_jurisdictions`) and enforced in app queries.  
6. **Every prediction references `model_version`**; explainability artifacts are first-class.  
7. **Soft-delete** only where historical reconstruction matters (`deleted_at`); audit is append-only.  
8. **Enums** for closed vocabularies; lookup tables when police codes may grow/change.  

---

## 2. Extensions (required)

| Extension | Purpose |
|-----------|---------|
| `postgis` | Geometry/geography types, spatial indexes, spatial functions |
| `vector` | Embedding columns for document/chunk RAG |
| `pgcrypto` | Optional: `gen_random_uuid()` if not using `pg_catalog` uuid |

**Recommended DB settings (ops, not schema):** adequate `shared_buffers`, `work_mem` for spatial joins; enable JIT cautiously.

---

## 3. Enumerations

PostgreSQL `CREATE TYPE ... AS ENUM`.

### 3.1 Identity & platform

| Enum | Values | Why |
|------|--------|-----|
| `user_status` | `active`, `invited`, `disabled` | Account lifecycle |
| `session_status` | `active`, `revoked`, `expired` | Refresh/session control |
| `job_status` | `queued`, `running`, `succeeded`, `failed`, `cancelled` | Async jobs |
| `job_type` | `ingest_postprocess`, `aggregate_refresh`, `cache_warm`, `embedding_upsert`, `report_generate`, `ml_score_trigger`, `other` | Job taxonomy |
| `audit_action` | `login`, `logout`, `create`, `read`, `update`, `delete`, `export`, `admin`, `ai_tool`, `ingest` | Audit vocabulary |
| `feature_flag_state` | `on`, `off`, `percentage` | Flag modes |

### 3.2 Organization

| Enum | Values | Why |
|------|--------|-----|
| `org_unit_type` | `state`, `range`, `district`, `subdivision`, `circle`, `station`, `beat` | Karnataka-style hierarchy flexibility |

### 3.3 Crime / incidents

| Enum | Values | Why |
|------|--------|-----|
| `incident_status` | `reported`, `registered`, `under_investigation`, `chargesheeted`, `closed`, `cancelled` | Case lifecycle (simplified for platform) |
| `incident_source` | `manual`, `csv_ingest`, `api_ingest`, `seed` | Provenance |
| `severity_level` | `low`, `medium`, `high`, `critical` | Operational triage |
| `person_involvement_role` | `accused`, `suspect`, `complainant`, `witness`, `victim`, `other` | Incident↔person edge role |
| `person_link_type` | `co_accused`, `associate`, `same_address`, `family`, `other` | Network edge type |
| `person_link_origin` | `derived`, `curated` | Auto vs analyst-confirmed |

### 3.4 Spatial / ML / decision / AI

| Enum | Values | Why |
|------|--------|-----|
| `geometry_layer_type` | `district_boundary`, `station_boundary`, `beat_boundary`, `hotspot`, `grid_cell`, `custom` | Layer catalog |
| `prediction_scope_type` | `state`, `district`, `station`, `grid_cell`, `hotspot` | Prediction grain |
| `prediction_metric` | `incident_count`, `risk_score`, `hotspot_intensity` | What was predicted |
| `model_task` | `forecast`, `risk`, `hotspot`, `repeat_offender`, `trend` | Model family |
| `model_status` | `training`, `shadow`, `production`, `retired`, `failed` | Model lifecycle |
| `hotspot_method` | `hdbscan`, `grid_density`, `kde`, `other` | Hotspot algorithm |
| `patrol_plan_status` | `draft`, `recommended`, `approved`, `rejected`, `archived` | Human-in-the-loop |
| `message_role` | `system`, `user`, `assistant`, `tool` | Chat messages |
| `tool_trace_status` | `ok`, `error`, `denied` | Agent tool outcomes |

---

## 4. Entity-Relationship Overview

```text
users ──┬── user_roles ──── roles ──── role_permissions ──── permissions
        └── user_jurisdictions ──── districts / police_stations

districts 1──* police_stations 1──* beats (optional)
police_stations 1──* incidents *──* persons (via incident_persons)
persons ── person_links ── persons

offense_categories 1──* offense_types 1──* incidents

incidents.location (geography Point)
districts.boundary / police_stations.boundary (geometry MultiPolygon)
police_stations.location (geography Point)

model_registry 1──* prediction_runs 1──* prediction_values
prediction_runs 1──* explanation_artifacts
hotspot_runs 1──* hotspot_features

conversations 1──* messages
messages 1──* tool_traces
document_chunks.embedding (vector)

patrol_plans 1──* patrol_plan_items
audit_events (append-only)
jobs
feature_flags
```

---

## 5. Tables (complete)

Convention for every table unless noted:
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `created_at timestamptz NOT NULL DEFAULT now()`
- `updated_at timestamptz NOT NULL DEFAULT now()`

---

### 5.1 Identity & access

#### `users`
| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `email` | `citext` or `text` | UNIQUE NOT NULL | Login identifier |
| `full_name` | `text` | NOT NULL | |
| `password_hash` | `text` | NULL | Null if SSO-only later |
| `status` | `user_status` | NOT NULL DEFAULT `active` | |
| `last_login_at` | `timestamptz` | NULL | |
| `deleted_at` | `timestamptz` | NULL | Soft delete |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL | |

**Indexes:**  
- `UNIQUE (email)`  
- `INDEX (status)`  
- `INDEX (deleted_at) WHERE deleted_at IS NULL` (partial)

#### `roles`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `code` | `text` | UNIQUE NOT NULL — e.g. `admin`, `sp`, `sho`, `analyst`, `control_room` |
| `name` | `text` | NOT NULL |
| `description` | `text` | NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

#### `permissions`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `code` | `text` | UNIQUE NOT NULL — e.g. `incident:read`, `ai:chat`, `admin:users` |
| `description` | `text` | NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

#### `role_permissions`
| Column | Type | Constraints |
|--------|------|-------------|
| `role_id` | `uuid` | FK → `roles.id` ON DELETE CASCADE |
| `permission_id` | `uuid` | FK → `permissions.id` ON DELETE CASCADE |
| `created_at` | `timestamptz` | NOT NULL |

**PK:** `(role_id, permission_id)`

#### `user_roles`
| Column | Type | Constraints |
|--------|------|-------------|
| `user_id` | `uuid` | FK → `users.id` ON DELETE CASCADE |
| `role_id` | `uuid` | FK → `roles.id` ON DELETE RESTRICT |
| `created_at` | `timestamptz` | NOT NULL |

**PK:** `(user_id, role_id)`  
**Indexes:** `INDEX (role_id)`

#### `user_jurisdictions`
ABAC scope: which districts/stations a user may access.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `user_id` | `uuid` | FK → `users.id` ON DELETE CASCADE |
| `district_id` | `uuid` | FK → `districts.id` ON DELETE CASCADE, NULL |
| `station_id` | `uuid` | FK → `police_stations.id` ON DELETE CASCADE, NULL |
| `created_at` | `timestamptz` | NOT NULL |

**CHECK:** `district_id IS NOT NULL OR station_id IS NOT NULL`  
**Indexes:**  
- `INDEX (user_id)`  
- `INDEX (district_id)`  
- `INDEX (station_id)`  
- `UNIQUE (user_id, district_id, station_id)` (nulls-not-distinct if PG15+; else application uniqueness)

#### `auth_sessions`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `user_id` | `uuid` | FK → `users.id` ON DELETE CASCADE |
| `refresh_token_hash` | `text` | UNIQUE NOT NULL |
| `status` | `session_status` | NOT NULL DEFAULT `active` |
| `user_agent` | `text` | NULL |
| `ip_inet` | `inet` | NULL |
| `expires_at` | `timestamptz` | NOT NULL |
| `revoked_at` | `timestamptz` | NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:**  
- `INDEX (user_id, status)`  
- `INDEX (expires_at)`  
- `INDEX (status) WHERE status = 'active'`

---

### 5.2 Organization & jurisdiction (spatial)

#### `districts`
| Column | Type | Constraints | Spatial |
|--------|------|-------------|---------|
| `id` | `uuid` | PK | |
| `code` | `text` | UNIQUE NOT NULL | e.g. `BLR`, `MYS` |
| `name` | `text` | NOT NULL | |
| `state_code` | `text` | NOT NULL DEFAULT `'KA'` | |
| `boundary` | `geometry(MultiPolygon, 4326)` | NULL | District polygon |
| `centroid` | `geography(Point, 4326)` | NULL | Optional derived |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` | Extra GIS attrs |
| `is_active` | `boolean` | NOT NULL DEFAULT true | |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL | |

**Indexes:**  
- `UNIQUE (code)`  
- `GIST (boundary)`  
- `GIST (centroid)`  
- `GIN (properties)` (only if queried)  
- `INDEX (state_code, is_active)`

#### `police_stations`
| Column | Type | Constraints | Spatial |
|--------|------|-------------|---------|
| `id` | `uuid` | PK | |
| `district_id` | `uuid` | FK → `districts.id` ON DELETE RESTRICT NOT NULL | |
| `code` | `text` | NOT NULL | Unique per district |
| `name` | `text` | NOT NULL | |
| `location` | `geography(Point, 4326)` | NULL | Station point |
| `boundary` | `geometry(MultiPolygon, 4326)` | NULL | Jurisdiction polygon |
| `address` | `text` | NULL | |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` | |
| `is_active` | `boolean` | NOT NULL DEFAULT true | |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL | |

**Constraints:** `UNIQUE (district_id, code)`  
**Indexes:**  
- `INDEX (district_id)`  
- `GIST (location)`  
- `GIST (boundary)`  
- `INDEX (is_active)`

#### `beats` (optional but modeled)
| Column | Type | Constraints | Spatial |
|--------|------|-------------|---------|
| `id` | `uuid` | PK | |
| `station_id` | `uuid` | FK → `police_stations.id` ON DELETE CASCADE NOT NULL | |
| `code` | `text` | NOT NULL | |
| `name` | `text` | NOT NULL | |
| `boundary` | `geometry(MultiPolygon, 4326)` | NULL | |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL | |

**Constraints:** `UNIQUE (station_id, code)`  
**Indexes:** `INDEX (station_id)`, `GIST (boundary)`

---

### 5.3 Offense taxonomy

#### `offense_categories`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `code` | `text` | UNIQUE NOT NULL |
| `name` | `text` | NOT NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

#### `offense_types`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `category_id` | `uuid` | FK → `offense_categories.id` ON DELETE RESTRICT NOT NULL |
| `code` | `text` | UNIQUE NOT NULL — IPC/BNS/local code |
| `name` | `text` | NOT NULL |
| `default_severity` | `severity_level` | NOT NULL DEFAULT `medium` |
| `is_cognizable` | `boolean` | NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (category_id)`, `INDEX (default_severity)`

---

### 5.4 Incidents (core fact table)

#### `incidents`
| Column | Type | Constraints | Spatial / notes |
|--------|------|-------------|-----------------|
| `id` | `uuid` | PK | |
| `external_ref` | `text` | NULL | FIR/CR number from source |
| `offense_type_id` | `uuid` | FK → `offense_types.id` RESTRICT NOT NULL | |
| `district_id` | `uuid` | FK → `districts.id` RESTRICT NOT NULL | Denormalized for AuthZ speed |
| `station_id` | `uuid` | FK → `police_stations.id` RESTRICT NOT NULL | |
| `beat_id` | `uuid` | FK → `beats.id` SET NULL NULL | |
| `status` | `incident_status` | NOT NULL DEFAULT `reported` | |
| `severity` | `severity_level` | NOT NULL | May override offense default |
| `source` | `incident_source` | NOT NULL DEFAULT `manual` | |
| `occurred_at` | `timestamptz` | NOT NULL | Event time |
| `reported_at` | `timestamptz` | NULL | |
| `registered_at` | `timestamptz` | NULL | |
| `title` | `text` | NULL | Short summary |
| `description` | `text` | NULL | |
| `location` | `geography(Point, 4326)` | NOT NULL | **Primary spatial field** |
| `location_accuracy_m` | `real` | NULL | |
| `address_text` | `text` | NULL | |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` | Flexible source fields |
| `ingest_batch_id` | `uuid` | NULL | FK → `ingest_batches.id` |
| `created_by` | `uuid` | FK → `users.id` SET NULL NULL | |
| `deleted_at` | `timestamptz` | NULL | |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL | |

**CHECK:** `occurred_at <= coalesce(reported_at, occurred_at)` (soft; optional)  
**Indexes (critical for PostGIS + analytics):**  
1. `GIST (location)` — radius / viewport / KNN  
2. `INDEX (occurred_at DESC)`  
3. `INDEX (station_id, occurred_at DESC)`  
4. `INDEX (district_id, occurred_at DESC)`  
5. `INDEX (offense_type_id, occurred_at DESC)`  
6. `INDEX (status)`  
7. `INDEX (severity)`  
8. `UNIQUE (external_ref) WHERE external_ref IS NOT NULL`  
9. `INDEX (ingest_batch_id)`  
10. `INDEX (deleted_at) WHERE deleted_at IS NULL`  
11. Optional BRIN `(occurred_at)` for very large append-only history  

**PostGIS query patterns this enables:**  
- Viewport: `location && ST_MakeEnvelope(... )::geography` / transform carefully — prefer `geometry` cast for bbox or use `ST_DWithin`  
- Radius: `ST_DWithin(location, ST_SetSRID(ST_MakePoint(lon,lat),4326)::geography, radius_m)`  
- Station containment join: `ST_Contains(station.boundary, incident.location::geometry)`

> **Spatial type choice:** `geography(Point,4326)` for incidents and station points → meter-accurate `ST_DWithin`. Boundaries as `geometry(MultiPolygon,4326)` → faster planar contains/intersects with GIST; convert as needed.

#### `incident_status_history`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `incident_id` | `uuid` | FK → `incidents.id` ON DELETE CASCADE |
| `from_status` | `incident_status` | NULL |
| `to_status` | `incident_status` | NOT NULL |
| `changed_by` | `uuid` | FK → `users.id` SET NULL NULL |
| `note` | `text` | NULL |
| `changed_at` | `timestamptz` | NOT NULL DEFAULT now() |

**Indexes:** `INDEX (incident_id, changed_at DESC)`

#### `ingest_batches`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `source` | `incident_source` | NOT NULL |
| `filename` | `text` | NULL |
| `row_count` | `integer` | NULL |
| `success_count` | `integer` | NULL |
| `error_count` | `integer` | NULL |
| `started_at` | `timestamptz` | NOT NULL DEFAULT now() |
| `finished_at` | `timestamptz` | NULL |
| `created_by` | `uuid` | FK → `users.id` SET NULL |
| `errors` | `jsonb` | NOT NULL DEFAULT `[]` |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

---

### 5.5 Persons & criminal network

#### `persons`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `external_ref` | `text` | NULL UNIQUE |
| `full_name` | `text` | NOT NULL |
| `alias` | `text` | NULL |
| `gender` | `text` | NULL |
| `dob` | `date` | NULL |
| `phone` | `text` | NULL |
| `address_text` | `text` | NULL |
| `home_location` | `geography(Point, 4326)` | NULL |
| `is_repeat_offender` | `boolean` | NOT NULL DEFAULT false |
| `risk_flags` | `jsonb` | NOT NULL DEFAULT `{}` |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` |
| `deleted_at` | `timestamptz` | NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:**  
- `INDEX (full_name)` (consider `pg_trgm` GIN later)  
- `GIST (home_location)`  
- `INDEX (is_repeat_offender) WHERE is_repeat_offender`  
- `GIN (risk_flags)` if filtered

#### `incident_persons`
| Column | Type | Constraints |
|--------|------|-------------|
| `incident_id` | `uuid` | FK → `incidents.id` ON DELETE CASCADE |
| `person_id` | `uuid` | FK → `persons.id` ON DELETE CASCADE |
| `role` | `person_involvement_role` | NOT NULL |
| `notes` | `text` | NULL |
| `created_at` | `timestamptz` | NOT NULL |

**PK:** `(incident_id, person_id, role)`  
**Indexes:** `INDEX (person_id)`, `INDEX (role)`

#### `person_links`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `person_a_id` | `uuid` | FK → `persons.id` ON DELETE CASCADE |
| `person_b_id` | `uuid` | FK → `persons.id` ON DELETE CASCADE |
| `link_type` | `person_link_type` | NOT NULL |
| `origin` | `person_link_origin` | NOT NULL DEFAULT `derived` |
| `weight` | `real` | NOT NULL DEFAULT 1.0 CHECK (weight >= 0) |
| `evidence_incident_id` | `uuid` | FK → `incidents.id` SET NULL NULL |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**CHECK:** `person_a_id <> person_b_id`  
**UNIQUE:** `(person_a_id, person_b_id, link_type)` (store canonical ordered pair in app: `a < b`)  
**Indexes:** `INDEX (person_a_id)`, `INDEX (person_b_id)`, `INDEX (link_type)`, `INDEX (weight DESC)`

---

### 5.6 Spatial derived layers

#### `grid_cells`
Precomputed analysis grid (e.g. H3-like hex approximated as polygon, or square grid).

| Column | Type | Constraints | Spatial |
|--------|------|-------------|---------|
| `id` | `uuid` | PK | |
| `district_id` | `uuid` | FK → `districts.id` RESTRICT NULL | |
| `cell_key` | `text` | UNIQUE NOT NULL | Stable external id |
| `resolution` | `integer` | NOT NULL | |
| `boundary` | `geometry(Polygon, 4326)` | NOT NULL | |
| `centroid` | `geography(Point, 4326)` | NOT NULL | |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL | |

**Indexes:** `GIST (boundary)`, `GIST (centroid)`, `INDEX (district_id, resolution)`

#### `spatial_layers` (catalog of published GeoJSON layers)
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `layer_type` | `geometry_layer_type` | NOT NULL |
| `name` | `text` | NOT NULL |
| `version` | `text` | NOT NULL |
| `district_id` | `uuid` | FK NULL |
| `metadata` | `jsonb` | NOT NULL DEFAULT `{}` |
| `is_current` | `boolean` | NOT NULL DEFAULT false |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (layer_type, is_current)`, `UNIQUE (name, version)`

#### `hotspot_runs`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `method` | `hotspot_method` | NOT NULL |
| `model_version` | `text` | NULL | Link to ML registry code |
| `district_id` | `uuid` | FK NULL |
| `window_start` | `timestamptz` | NOT NULL |
| `window_end` | `timestamptz` | NOT NULL |
| `params` | `jsonb` | NOT NULL DEFAULT `{}` |
| `metrics` | `jsonb` | NOT NULL DEFAULT `{}` |
| `is_current` | `boolean` | NOT NULL DEFAULT false |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (district_id, is_current)`, `INDEX (window_start, window_end)`

#### `hotspot_features`
| Column | Type | Constraints | Spatial |
|--------|------|-------------|---------|
| `id` | `uuid` | PK | |
| `hotspot_run_id` | `uuid` | FK → `hotspot_runs.id` ON DELETE CASCADE | |
| `rank` | `integer` | NOT NULL | |
| `score` | `double precision` | NOT NULL | |
| `incident_count` | `integer` | NOT NULL DEFAULT 0 | |
| `geom` | `geometry(Geometry, 4326)` | NOT NULL | Point or Polygon cluster |
| `centroid` | `geography(Point, 4326)` | NOT NULL | |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` | |
| `created_at` | `timestamptz` | NOT NULL | |

**Indexes:**  
- `INDEX (hotspot_run_id, rank)`  
- `GIST (geom)`  
- `GIST (centroid)`  
- `INDEX (score DESC)`

---

### 5.7 Machine learning & predictions

#### `model_registry`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `model_code` | `text` | NOT NULL | e.g. `risk_lgbm` |
| `model_version` | `text` | NOT NULL | Semver / timestamp |
| `task` | `model_task` | NOT NULL |
| `algorithm` | `text` | NOT NULL | `lightgbm`, `xgboost`, `statsforecast`, `hdbscan` |
| `status` | `model_status` | NOT NULL DEFAULT `training` |
| `train_window_start` | `timestamptz` | NULL |
| `train_window_end` | `timestamptz` | NULL |
| `metrics` | `jsonb` | NOT NULL DEFAULT `{}` | MAE, RMSE, PR-AUC, etc. |
| `feature_list` | `jsonb` | NOT NULL DEFAULT `[]` | |
| `artifact_uri` | `text` | NULL | Path/S3 key |
| `created_by` | `uuid` | FK → `users.id` SET NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Constraints:** `UNIQUE (model_code, model_version)`  
**Indexes:** `INDEX (task, status)`, `INDEX (status) WHERE status = 'production'`

#### `feature_runs`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `name` | `text` | NOT NULL |
| `params` | `jsonb` | NOT NULL DEFAULT `{}` |
| `row_count` | `bigint` | NULL |
| `started_at` / `finished_at` | `timestamptz` | |
| `status` | `job_status` | NOT NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

#### `prediction_runs`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `model_id` | `uuid` | FK → `model_registry.id` RESTRICT NOT NULL |
| `feature_run_id` | `uuid` | FK → `feature_runs.id` SET NULL NULL |
| `scope_type` | `prediction_scope_type` | NOT NULL |
| `metric` | `prediction_metric` | NOT NULL |
| `horizon_start` | `timestamptz` | NOT NULL |
| `horizon_end` | `timestamptz` | NOT NULL |
| `generated_at` | `timestamptz` | NOT NULL DEFAULT now() |
| `is_current` | `boolean` | NOT NULL DEFAULT false |
| `notes` | `text` | NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (model_id)`, `INDEX (scope_type, metric, is_current)`, `INDEX (horizon_start, horizon_end)`

#### `prediction_values`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `prediction_run_id` | `uuid` | FK → `prediction_runs.id` ON DELETE CASCADE |
| `district_id` | `uuid` | FK NULL |
| `station_id` | `uuid` | FK NULL |
| `grid_cell_id` | `uuid` | FK → `grid_cells.id` SET NULL NULL |
| `hotspot_feature_id` | `uuid` | FK → `hotspot_features.id` SET NULL NULL |
| `value` | `double precision` | NOT NULL | Count or score |
| `lower_bound` | `double precision` | NULL | Uncertainty |
| `upper_bound` | `double precision` | NULL |
| `occurs_on` | `date` | NULL | For daily forecast buckets |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` |
| `created_at` | `timestamptz` | NOT NULL |

**CHECK:** at least one scope FK not null (district/station/grid/hotspot)  
**Indexes:**  
- `INDEX (prediction_run_id)`  
- `INDEX (district_id, occurs_on)`  
- `INDEX (station_id, occurs_on)`  
- `INDEX (grid_cell_id, occurs_on)`  
- `INDEX (value DESC)`  
- `UNIQUE (prediction_run_id, station_id, occurs_on)` WHERE station scoped  
- similar partial uniques for district/grid

#### `explanation_artifacts`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `prediction_run_id` | `uuid` | FK → `prediction_runs.id` ON DELETE CASCADE |
| `prediction_value_id` | `uuid` | FK → `prediction_values.id` ON DELETE CASCADE NULL |
| `shap_global` | `jsonb` | NULL | Global importances |
| `shap_local` | `jsonb` | NULL | Per-row contributions |
| `artifact_uri` | `text` | NULL | Large blob off-DB |
| `summary_text` | `text` | NULL | Optional precomputed narrative seed |
| `created_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (prediction_run_id)`, `INDEX (prediction_value_id)`

---

### 5.8 Decision support (patrol)

#### `patrol_plans`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `district_id` | `uuid` | FK → `districts.id` RESTRICT NOT NULL |
| `status` | `patrol_plan_status` | NOT NULL DEFAULT `draft` |
| `title` | `text` | NOT NULL |
| `horizon_start` / `horizon_end` | `timestamptz` | NOT NULL |
| `prediction_run_id` | `uuid` | FK → `prediction_runs.id` SET NULL |
| `hotspot_run_id` | `uuid` | FK → `hotspot_runs.id` SET NULL |
| `created_by` | `uuid` | FK → `users.id` SET NULL |
| `approved_by` | `uuid` | FK → `users.id` SET NULL |
| `approved_at` | `timestamptz` | NULL |
| `rationale` | `text` | NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (district_id, status)`, `INDEX (horizon_start, horizon_end)`

#### `patrol_plan_items`
| Column | Type | Constraints | Spatial |
|--------|------|-------------|---------|
| `id` | `uuid` | PK | |
| `patrol_plan_id` | `uuid` | FK → `patrol_plans.id` ON DELETE CASCADE | |
| `rank` | `integer` | NOT NULL | |
| `station_id` | `uuid` | FK NULL | |
| `hotspot_feature_id` | `uuid` | FK NULL | |
| `grid_cell_id` | `uuid` | FK NULL | |
| `target_geom` | `geography(Point, 4326)` | NULL | Patrol focus point |
| `recommended_units` | `integer` | NULL | Abstract capacity |
| `time_window_start` / `time_window_end` | `timestamptz` | NULL | |
| `score` | `double precision` | NOT NULL | |
| `explanation` | `text` | NULL | |
| `created_at` | `timestamptz` | NOT NULL | |

**Indexes:** `INDEX (patrol_plan_id, rank)`, `GIST (target_geom)`

---

### 5.9 AI / RAG / copilot

#### `documents`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `title` | `text` | NOT NULL |
| `source_uri` | `text` | NULL |
| `doc_type` | `text` | NOT NULL | `sop`, `model_card`, `brief`, `glossary` |
| `jurisdiction_district_id` | `uuid` | FK NULL | Scope docs |
| `metadata` | `jsonb` | NOT NULL DEFAULT `{}` |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

#### `document_chunks`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `document_id` | `uuid` | FK → `documents.id` ON DELETE CASCADE |
| `chunk_index` | `integer` | NOT NULL |
| `content` | `text` | NOT NULL |
| `token_count` | `integer` | NULL |
| `embedding` | `vector(1536)` | NULL | Dimension locked to embedding model |
| `metadata` | `jsonb` | NOT NULL DEFAULT `{}` |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Constraints:** `UNIQUE (document_id, chunk_index)`  
**Indexes:**  
- `INDEX (document_id)`  
- **HNSW** or **IVFFlat** on `embedding` — prefer `hnsw (embedding vector_cosine_ops)` for S0–S1  
- `GIN (metadata)` if filtered

> Dimension `1536` is a design default; adjust to the chosen Gemini embedding size and keep a single dimension per table (or versioned tables).

#### `conversations`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `user_id` | `uuid` | FK → `users.id` ON DELETE CASCADE |
| `title` | `text` | NULL |
| `district_id` | `uuid` | FK NULL | Active jurisdiction context |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (user_id, updated_at DESC)`

#### `messages`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `conversation_id` | `uuid` | FK → `conversations.id` ON DELETE CASCADE |
| `role` | `message_role` | NOT NULL |
| `content` | `text` | NOT NULL |
| `citations` | `jsonb` | NOT NULL DEFAULT `[]` | Grounding refs |
| `token_usage` | `jsonb` | NULL | |
| `created_at` | `timestamptz` | NOT NULL DEFAULT now() |

**Indexes:** `INDEX (conversation_id, created_at)`

#### `tool_traces`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `message_id` | `uuid` | FK → `messages.id` ON DELETE CASCADE |
| `tool_name` | `text` | NOT NULL |
| `status` | `tool_trace_status` | NOT NULL |
| `request_payload` | `jsonb` | NOT NULL DEFAULT `{}` |
| `response_payload` | `jsonb` | NOT NULL DEFAULT `{}` |
| `latency_ms` | `integer` | NULL |
| `created_at` | `timestamptz` | NOT NULL DEFAULT now() |

**Indexes:** `INDEX (message_id)`, `INDEX (tool_name, created_at DESC)`

---

### 5.10 Platform: audit, jobs, flags

#### `audit_events` (append-only — no `updated_at`)
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `actor_user_id` | `uuid` | FK → `users.id` SET NULL NULL |
| `action` | `audit_action` | NOT NULL |
| `resource_type` | `text` | NOT NULL |
| `resource_id` | `text` | NULL |
| `district_id` | `uuid` | FK NULL |
| `ip_inet` | `inet` | NULL |
| `user_agent` | `text` | NULL |
| `request_id` | `text` | NULL |
| `payload` | `jsonb` | NOT NULL DEFAULT `{}` |
| `created_at` | `timestamptz` | NOT NULL DEFAULT now() |

**Indexes:**  
- `INDEX (created_at DESC)`  
- `INDEX (actor_user_id, created_at DESC)`  
- `INDEX (resource_type, resource_id)`  
- `INDEX (action, created_at DESC)`  
- BRIN `(created_at)` at scale  

#### `jobs`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `job_type` | `job_type` | NOT NULL |
| `status` | `job_status` | NOT NULL DEFAULT `queued` |
| `payload` | `jsonb` | NOT NULL DEFAULT `{}` |
| `result` | `jsonb` | NOT NULL DEFAULT `{}` |
| `idempotency_key` | `text` | UNIQUE NULL |
| `attempts` | `integer` | NOT NULL DEFAULT 0 |
| `scheduled_at` | `timestamptz` | NULL |
| `started_at` / `finished_at` | `timestamptz` | NULL |
| `error` | `text` | NULL |
| `created_by` | `uuid` | FK SET NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Indexes:** `INDEX (status, scheduled_at)`, `INDEX (job_type, created_at DESC)`

#### `feature_flags`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `key` | `text` | UNIQUE NOT NULL — `AI_ENABLED`, `ML_ENABLED` |
| `state` | `feature_flag_state` | NOT NULL DEFAULT `off` |
| `percentage` | `integer` | NULL CHECK (0–100) |
| `description` | `text` | NULL |
| `updated_by` | `uuid` | FK SET NULL |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

---

### 5.11 Socio-economic correlation (datathon capability)

Bridges district socio-economic drivers with crime intensity for correlation analytics.

#### `socio_economic_indicators`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `district_id` | `uuid` | FK → `districts.id` ON DELETE CASCADE NOT NULL |
| `year` | `integer` | NOT NULL |
| `indicator_code` | `text` | NOT NULL — e.g. `unemployment_rate`, `literacy_rate`, `population_density`, `poverty_index`, `urban_pct` |
| `value` | `double precision` | NOT NULL |
| `unit` | `text` | NOT NULL — `%`, `per_km2`, `index` |
| `source` | `text` | NULL — census / survey citation |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Constraints:** `UNIQUE (district_id, year, indicator_code)`  
**Indexes:** `INDEX (year, indicator_code)`, `INDEX (district_id, year)`

#### `district_crime_metrics`
Yearly crime intensity per district (materialized from incidents later; seedable for demos).

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `district_id` | `uuid` | FK → `districts.id` ON DELETE CASCADE NOT NULL |
| `year` | `integer` | NOT NULL |
| `incident_count` | `integer` | NOT NULL DEFAULT 0 |
| `crime_rate_per_100k` | `double precision` | NOT NULL |
| `high_severity_count` | `integer` | NOT NULL DEFAULT 0 |
| `properties` | `jsonb` | NOT NULL DEFAULT `{}` |
| `created_at` / `updated_at` | `timestamptz` | NOT NULL |

**Constraints:** `UNIQUE (district_id, year)`  
**Indexes:** `INDEX (year)`, `INDEX (crime_rate_per_100k DESC)`

#### `socio_crime_correlations`
Cached correlation results (optional materialization of compute jobs).

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `uuid` | PK |
| `year` | `integer` | NOT NULL |
| `indicator_code` | `text` | NOT NULL |
| `crime_metric` | `text` | NOT NULL — `crime_rate_per_100k` \| `incident_count` |
| `coefficient` | `double precision` | NOT NULL — Pearson r |
| `abs_coefficient` | `double precision` | NOT NULL |
| `sample_size` | `integer` | NOT NULL |
| `method` | `text` | NOT NULL DEFAULT `pearson` |
| `computed_at` | `timestamptz` | NOT NULL DEFAULT now() |
| `created_at` | `timestamptz` | NOT NULL |

**Constraints:** `UNIQUE (year, indicator_code, crime_metric, method)`  
**Indexes:** `INDEX (year, abs_coefficient DESC)`

### 5.12 Analytics helpers (controlled denormalization)

Not required for v1 correctness; recommended for scale.

#### `agg_incident_daily` (materialized table or matview target)
| Column | Type | Constraints |
|--------|------|-------------|
| `day` | `date` | NOT NULL |
| `district_id` | `uuid` | NOT NULL |
| `station_id` | `uuid` | NOT NULL |
| `offense_type_id` | `uuid` | NOT NULL |
| `incident_count` | `integer` | NOT NULL |
| `updated_at` | `timestamptz` | NOT NULL |

**PK:** `(day, station_id, offense_type_id)`  
**Indexes:** `INDEX (district_id, day)`, `INDEX (station_id, day)`

#### `agg_incident_hex` (optional map pre-agg)
| Column | Type | Notes |
|--------|------|-------|
| `day` | `date` | |
| `grid_cell_id` | `uuid` | FK → grid_cells |
| `offense_type_id` | `uuid` | NULL = all |
| `incident_count` | `integer` | |
| **PK** | `(day, grid_cell_id, offense_type_id)` | |

---

## 6. Foreign Key Map (complete)

| From | To | On delete |
|------|----|-----------|
| `role_permissions.role_id` | `roles.id` | CASCADE |
| `role_permissions.permission_id` | `permissions.id` | CASCADE |
| `user_roles.user_id` | `users.id` | CASCADE |
| `user_roles.role_id` | `roles.id` | RESTRICT |
| `user_jurisdictions.user_id` | `users.id` | CASCADE |
| `user_jurisdictions.district_id` | `districts.id` | CASCADE |
| `user_jurisdictions.station_id` | `police_stations.id` | CASCADE |
| `auth_sessions.user_id` | `users.id` | CASCADE |
| `police_stations.district_id` | `districts.id` | RESTRICT |
| `beats.station_id` | `police_stations.id` | CASCADE |
| `offense_types.category_id` | `offense_categories.id` | RESTRICT |
| `incidents.offense_type_id` | `offense_types.id` | RESTRICT |
| `incidents.district_id` | `districts.id` | RESTRICT |
| `incidents.station_id` | `police_stations.id` | RESTRICT |
| `incidents.beat_id` | `beats.id` | SET NULL |
| `incidents.ingest_batch_id` | `ingest_batches.id` | SET NULL |
| `incidents.created_by` | `users.id` | SET NULL |
| `incident_status_history.incident_id` | `incidents.id` | CASCADE |
| `incident_status_history.changed_by` | `users.id` | SET NULL |
| `ingest_batches.created_by` | `users.id` | SET NULL |
| `incident_persons.incident_id` | `incidents.id` | CASCADE |
| `incident_persons.person_id` | `persons.id` | CASCADE |
| `person_links.person_a_id` / `person_b_id` | `persons.id` | CASCADE |
| `person_links.evidence_incident_id` | `incidents.id` | SET NULL |
| `grid_cells.district_id` | `districts.id` | RESTRICT |
| `spatial_layers.district_id` | `districts.id` | SET NULL |
| `hotspot_runs.district_id` | `districts.id` | SET NULL |
| `hotspot_features.hotspot_run_id` | `hotspot_runs.id` | CASCADE |
| `model_registry.created_by` | `users.id` | SET NULL |
| `prediction_runs.model_id` | `model_registry.id` | RESTRICT |
| `prediction_runs.feature_run_id` | `feature_runs.id` | SET NULL |
| `prediction_values.prediction_run_id` | `prediction_runs.id` | CASCADE |
| `prediction_values.district_id` | `districts.id` | SET NULL |
| `prediction_values.station_id` | `police_stations.id` | SET NULL |
| `prediction_values.grid_cell_id` | `grid_cells.id` | SET NULL |
| `prediction_values.hotspot_feature_id` | `hotspot_features.id` | SET NULL |
| `explanation_artifacts.prediction_run_id` | `prediction_runs.id` | CASCADE |
| `explanation_artifacts.prediction_value_id` | `prediction_values.id` | CASCADE |
| `patrol_plans.*` | districts/users/prediction_runs/hotspot_runs | as above |
| `patrol_plan_items.*` | plans/stations/hotspots/grids | CASCADE from plan |
| `document_chunks.document_id` | `documents.id` | CASCADE |
| `documents.jurisdiction_district_id` | `districts.id` | SET NULL |
| `conversations.user_id` | `users.id` | CASCADE |
| `messages.conversation_id` | `conversations.id` | CASCADE |
| `tool_traces.message_id` | `messages.id` | CASCADE |
| `audit_events.actor_user_id` | `users.id` | SET NULL |
| `jobs.created_by` | `users.id` | SET NULL |
| `feature_flags.updated_by` | `users.id` | SET NULL |

---

## 7. Spatial Field Inventory

| Table | Column | Type | Index | Primary use |
|-------|--------|------|-------|-------------|
| `districts` | `boundary` | `geometry(MultiPolygon,4326)` | GIST | District mapping, contains |
| `districts` | `centroid` | `geography(Point,4326)` | GIST | Labels / distance |
| `police_stations` | `location` | `geography(Point,4326)` | GIST | Station markers |
| `police_stations` | `boundary` | `geometry(MultiPolygon,4326)` | GIST | Jurisdiction |
| `beats` | `boundary` | `geometry(MultiPolygon,4326)` | GIST | Beat mapping |
| `incidents` | `location` | `geography(Point,4326)` | GIST | Heat/cluster/radius/bbox |
| `persons` | `home_location` | `geography(Point,4326)` | GIST | Optional person geo |
| `grid_cells` | `boundary` | `geometry(Polygon,4326)` | GIST | Grid join |
| `grid_cells` | `centroid` | `geography(Point,4326)` | GIST | Risk map |
| `hotspot_features` | `geom` | `geometry(Geometry,4326)` | GIST | Hotspot polygons/points |
| `hotspot_features` | `centroid` | `geography(Point,4326)` | GIST | Ranking / distance |
| `patrol_plan_items` | `target_geom` | `geography(Point,4326)` | GIST | Patrol focus |

**Vector field:** `document_chunks.embedding vector(N)` + HNSW cosine index.

---

## 8. PostGIS Optimization Rules

1. **Points that need meter distances → `geography`.**  
2. **Boundaries for contains/intersects → `geometry` + GIST.**  
3. **Never `SELECT *` all incidents to the browser** — always bbox / radius / aggregated hex.  
4. **Viewport queries:** filter by `occurred_at` + district/station **before or with** spatial predicate.  
5. **Prefer `ST_DWithin` on geography** over `ST_Distance < r` (index-friendly).  
6. **Simplify boundaries** for overview layers (`ST_SimplifyPreserveTopology`) in published layer versions, not in base authoritative polygons.  
7. **Partition `incidents` by `RANGE (occurred_at)`** when row count exceeds ~5–10M (future).  
8. **Materialize** `agg_incident_daily` / hex for dashboards and low-zoom maps.  
9. **Keep `district_id` on incidents** even though derivable via station — AuthZ and aggregates stay cheap.  
10. **Validate SRID** on write: reject non-4326.

---

## 9. Index Summary (must-have set)

### B-tree / composite
- All FK columns  
- `incidents (station_id, occurred_at DESC)`  
- `incidents (district_id, occurred_at DESC)`  
- `incidents (offense_type_id, occurred_at DESC)`  
- `prediction_values` scope + date composites  
- `audit_events (actor_user_id, created_at DESC)`  
- `jobs (status, scheduled_at)`

### GIST
- Every geometry/geography column listed in §7

### GIN
- Selective `jsonb` columns actually filtered (`incidents.properties` only if needed)  
- Optional `pg_trgm` on `persons.full_name`

### Vector
- HNSW on `document_chunks.embedding`

### Partial
- Active users, active sessions, non-deleted incidents, `is_current` prediction/hotspot runs, production models

---

## 10. Table Count Checklist

| Domain | Tables |
|--------|--------|
| Identity | `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `user_jurisdictions`, `auth_sessions` |
| Org | `districts`, `police_stations`, `beats` |
| Offense | `offense_categories`, `offense_types` |
| Incidents | `incidents`, `incident_status_history`, `ingest_batches` |
| Network | `persons`, `incident_persons`, `person_links` |
| Spatial derived | `grid_cells`, `spatial_layers`, `hotspot_runs`, `hotspot_features` |
| ML | `model_registry`, `feature_runs`, `prediction_runs`, `prediction_values`, `explanation_artifacts` |
| Decision | `patrol_plans`, `patrol_plan_items` |
| AI | `documents`, `document_chunks`, `conversations`, `messages`, `tool_traces` |
| Platform | `audit_events`, `jobs`, `feature_flags` |
| Analytics | `agg_incident_daily`, `agg_incident_hex` |
| Socio-economic | `socio_economic_indicators`, `district_crime_metrics`, `socio_crime_correlations` |

**Total: 40 tables** (+ enums in §3).

---

## 11. Explicitly Out of Scope (for this design phase)

- SQLAlchemy models  
- Alembic migration Python  
- FastAPI repositories  
- Seed SQL data dumps  
- Running `CREATE TABLE` against a live database  

DDL may be implemented in a later phase from this specification.

---

## 12. Approval Gate

Confirm or amend:

1. `geography` for incident points + `geometry` for boundaries  
2. `district_id` denormalized on `incidents`  
3. pgvector on `document_chunks` (no Qdrant table)  
4. Enum set completeness for Karnataka datathon (IPC/BNS codes live in `offense_types`, not enums)  
5. 37-table inventory  

**STOP — awaiting approval before OpenAPI catalog or Alembic implementation.**
