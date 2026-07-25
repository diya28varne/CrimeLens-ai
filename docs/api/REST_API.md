# CrimeLens AI — REST API Design

**Status:** Design specification only (no FastAPI/router implementation)  
**Base path:** `/api/v1`  
**Style:** Resource-oriented REST + a few RPC-style action endpoints  
**Contract source of truth:** OpenAPI 3.1 (to be generated from this doc at implementation)  
**Auth default:** Browser httpOnly cookie session; `Authorization: Bearer` supported for non-browser clients  
**Content-Type:** `application/json` unless noted (GeoJSON, SSE)

---

## 0. Cross-cutting conventions

### 0.1 Headers

| Header | Direction | Purpose |
|--------|-----------|---------|
| `X-Request-Id` | both | Correlation ID (server generates if missing) |
| `Authorization` | req | `Bearer <access_token>` (optional if cookie session) |
| `Cookie` | req | `cl_access` / `cl_refresh` (httpOnly) |
| `Idempotency-Key` | req | Required on ingest/admin mutations |

### 0.2 Standard error model

```json
{
  "error": {
    "code": "FORBIDDEN_JURISDICTION",
    "message": "Human-readable summary",
    "details": {},
    "request_id": "uuid"
  }
}
```

| HTTP | When |
|------|------|
| 400 | Validation failure |
| 401 | Unauthenticated |
| 403 | Authenticated but not authorized / wrong jurisdiction |
| 404 | Resource not found **or** hidden by AuthZ (no leakage) |
| 409 | Conflict (duplicate external_ref, idempotency replay mismatch) |
| 422 | Semantic domain rule violation |
| 429 | Rate limited |
| 503 | Dependency degraded (AI/Gemini) with structured code |

### 0.3 Pagination

**Cursor pagination** (preferred for incidents/audit):

Request: `?limit=50&cursor=<opaque>`  
Response envelope:

```json
{
  "data": [],
  "page": {
    "next_cursor": "opaque-or-null",
    "limit": 50
  }
}
```

**Offset pagination** allowed for small admin lists: `?limit=&offset=` + `total`.

### 0.4 Common query filters

| Param | Type | Notes |
|-------|------|-------|
| `district_id` | uuid | AuthZ-scoped; ignored/denied if outside user jurisdictions |
| `station_id` | uuid | Same |
| `from` / `to` | ISO-8601 timestamptz | Inclusive start, exclusive end preferred |
| `offense_type_id` | uuid | Repeatable or comma-separated |
| `bbox` | `minLon,minLat,maxLon,maxLat` | EPSG:4326 |
| `lon` / `lat` / `radius_m` | number | Radius search |

### 0.5 AuthContext (implicit on every authenticated call)

Derived server-side from session/JWT — **never trusted from client body**:

- `user_id`
- `roles[]`
- `permissions[]`
- `allowed_district_ids[]`
- `allowed_station_ids[]`

All Crime/Prediction/Analytics/Network/AI reads are filtered by this context.

### 0.6 Envelope variants

| Kind | Shape |
|------|-------|
| Object | `{ "data": { ... } }` |
| List | `{ "data": [ ... ], "page": { ... } }` |
| Action | `{ "data": { ... }, "meta": { ... } }` |
| GeoJSON | raw `FeatureCollection` (no envelope) for map clients |
| SSE | `text/event-stream` for AI chat |

---

## 1. Authentication APIs

Base: `/api/v1/auth`

### 1.1 `POST /auth/login`

Authenticate with email/password; set httpOnly cookies; optionally return tokens for API clients.

**Request `LoginRequest`**

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `email` | string(email) | yes | |
| `password` | string | yes | min length enforced server-side |
| `client` | `"browser"` \| `"api"` | no | default `browser` |

**Response `LoginResponse`** `200`

| Field | Type | Notes |
|-------|------|-------|
| `data.user` | `UserPublic` | Profile |
| `data.access_token` | string \| null | Present when `client=api` |
| `data.expires_at` | string(datetime) | Access expiry |
| `data.permissions` | string[] | Convenience for UI gating |

Sets cookies when `client=browser`: `cl_access`, `cl_refresh`.

**Errors:** `401 INVALID_CREDENTIALS`, `403 USER_DISABLED`

---

### 1.2 `POST /auth/refresh`

Rotate refresh credential; issue new access.

**Request `RefreshRequest`**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `refresh_token` | string | conditional | Required for `api` clients; browser uses cookie |

**Response `RefreshResponse`** `200` — same token fields as login (user optional).

**Errors:** `401 SESSION_REVOKED`, `401 SESSION_EXPIRED`

---

### 1.3 `POST /auth/logout`

Revoke current session.

**Request:** empty body `{}`  
**Response:** `204 No Content`

---

### 1.4 `GET /auth/me`

Current principal + jurisdictions.

**Response `MeResponse`** `200`

```json
{
  "data": {
    "user": { "id": "...", "email": "...", "full_name": "...", "status": "active" },
    "roles": ["analyst"],
    "permissions": ["incident:read", "prediction:read", "ai:chat"],
    "jurisdictions": {
      "district_ids": ["..."],
      "station_ids": ["..."]
    }
  }
}
```

---

### Shared auth models

#### `UserPublic`
| Field | Type |
|-------|------|
| `id` | uuid |
| `email` | string |
| `full_name` | string |
| `status` | `active` \| `invited` \| `disabled` |

---

## 2. Organization (supporting Crime/Map)

Base: `/api/v1/org`  
Required for dropdowns/maps; AuthZ filtered.

### 2.1 `GET /org/districts`

**Query:** `q` (search), `is_active`  
**Response:** `{ "data": District[] }`

#### `District`
| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `code` | string | |
| `name` | string | |
| `state_code` | string | |
| `has_boundary` | boolean | Avoid sending full polygon in list |
| `centroid` | `GeoPoint` \| null | `{ "lon", "lat" }` |

### 2.2 `GET /org/districts/{district_id}`

Includes optional GeoJSON boundary when `?include=boundary`.

### 2.3 `GET /org/stations`

**Query:** `district_id` (required unless user has single district), `q`, `is_active`  
**Response:** `{ "data": Station[] }`

#### `Station`
| Field | Type |
|-------|------|
| `id` | uuid |
| `district_id` | uuid |
| `code` | string |
| `name` | string |
| `location` | `GeoPoint` \| null |
| `has_boundary` | boolean |

### 2.4 `GET /org/stations/{station_id}`

Optional `?include=boundary`.

---

## 3. Crime APIs

Base: `/api/v1/incidents` (+ spatial under `/api/v1/spatial`)

Permissions: `incident:read`, `incident:write`, `incident:ingest`

### 3.1 `GET /incidents`

Search/list incidents (non-GeoJSON tabular).

**Query `IncidentSearchQuery`**

| Param | Type | Notes |
|-------|------|-------|
| `district_id` | uuid | |
| `station_id` | uuid | |
| `offense_type_id` | uuid[] | |
| `status` | enum[] | |
| `severity` | enum[] | |
| `from` / `to` | datetime | on `occurred_at` |
| `q` | string | external_ref / title search |
| `limit` / `cursor` | | |

**Response `IncidentListResponse`**

```json
{
  "data": [ /* IncidentSummary */ ],
  "page": { "next_cursor": "...", "limit": 50 }
}
```

#### `IncidentSummary`
| Field | Type |
|-------|------|
| `id` | uuid |
| `external_ref` | string \| null |
| `offense_type` | `{ id, code, name }` |
| `district_id` | uuid |
| `station_id` | uuid |
| `status` | enum |
| `severity` | enum |
| `occurred_at` | datetime |
| `location` | `GeoPoint` |
| `title` | string \| null |

---

### 3.2 `GET /incidents/{incident_id}`

**Response `IncidentDetailResponse`** — `IncidentDetail`

#### `IncidentDetail` extends `IncidentSummary` with:
| Field | Type |
|-------|------|
| `description` | string \| null |
| `reported_at` / `registered_at` | datetime \| null |
| `address_text` | string \| null |
| `source` | enum |
| `properties` | object |
| `persons` | `IncidentPerson[]` |
| `status_history` | `StatusHistoryItem[]` |

#### `IncidentPerson`
| Field | Type |
|-------|------|
| `person_id` | uuid |
| `full_name` | string |
| `role` | enum |
| `is_repeat_offender` | boolean |

PII fields beyond name gated by permission `person:read_sensitive` (phone/dob omitted otherwise).

---

### 3.3 `GET /spatial/incidents`

Map viewport / radius GeoJSON feed.

**Query `SpatialIncidentQuery`**

| Param | Required | Notes |
|-------|----------|-------|
| `bbox` **or** (`lon`,`lat`,`radius_m`) | one mode | |
| `from` / `to` | recommended | |
| `district_id` / `station_id` | optional | |
| `offense_type_id` | optional | |
| `cluster` | optional | `true` at low zoom → clustered features |
| `limit` | optional | hard cap (e.g. 5000) |

**Response:** `application/geo+json` **FeatureCollection**

Feature properties:
| Property | Type |
|----------|------|
| `id` | uuid |
| `offense_code` | string |
| `severity` | enum |
| `occurred_at` | datetime |
| `station_id` | uuid |
| `cluster_count` | number \| omit | when clustered |

---

### 3.4 `GET /spatial/layers/{layer_key}`

Published layers: `districts`, `stations`, `hotspots_current`, `grid_risk_current`.

**Query:** `district_id`, `bbox`  
**Response:** GeoJSON FeatureCollection

---

### 3.5 `GET /spatial/radius`

Convenience RPC for control-room radius search (JSON, not only GeoJSON).

**Query:** `lon`, `lat`, `radius_m`, filters as above  
**Response:** `{ "data": { "count": n, "incidents": IncidentSummary[] } }`

---

### 3.6 `POST /incidents/ingest`

Batch CSV/JSON ingest (admin/analyst with `incident:ingest`).

**Request `IncidentIngestRequest`**

| Field | Type | Notes |
|-------|------|-------|
| `format` | `"json"` \| `"csv_inline"` | |
| `rows` | `IncidentIngestRow[]` | for json |
| `csv_text` | string | for csv_inline |
| `dry_run` | boolean | default false |

#### `IncidentIngestRow`
| Field | Type | Required |
|-------|------|----------|
| `external_ref` | string | recommended |
| `offense_code` | string | yes |
| `station_code` | string | yes |
| `occurred_at` | datetime | yes |
| `lon` / `lat` | number | yes |
| `status` | enum | no |
| `severity` | enum | no |
| `title` / `description` | string | no |
| `properties` | object | no |

**Response `IncidentIngestResponse`** `202` (async) or `200` (small sync)

| Field | Type |
|-------|------|
| `data.batch_id` | uuid |
| `data.accepted` | integer |
| `data.rejected` | integer |
| `data.errors` | `{ row, code, message }[]` |
| `data.job_id` | uuid \| null | postprocess job |

Requires `Idempotency-Key`.

---

### 3.7 `GET /incidents/ingest/batches/{batch_id}`

Ingest status.

**Response:** `IngestBatchStatus` — counts, errors, timestamps.

---

### 3.8 `GET /offense-types`

Taxonomy for filters.

**Response:** `{ "data": OffenseType[] }`  
`OffenseType`: `id`, `code`, `name`, `category`, `default_severity`

---

## 4. Dashboard APIs

Base: `/api/v1/dashboard`  
Purpose: **first-screen KPIs** — small, cacheable payloads.  
Permission: `analytics:read`

### 4.1 `GET /dashboard/overview`

**Query `DashboardOverviewQuery`**

| Param | Type | Default |
|-------|------|---------|
| `district_id` | uuid | user’s primary / required if multi |
| `station_id` | uuid | optional |
| `from` / `to` | datetime | last 30 days |

**Response `DashboardOverviewResponse`**

```json
{
  "data": {
    "scope": { "district_id": "...", "station_id": null, "from": "...", "to": "..." },
    "kpis": {
      "total_incidents": 1250,
      "total_incidents_delta_pct": -4.2,
      "open_incidents": 180,
      "high_severity": 64,
      "hotspot_count": 7,
      "avg_risk_score": 0.61
    },
    "by_severity": [{ "severity": "high", "count": 64 }],
    "by_offense_top": [{ "offense_type_id": "...", "name": "Theft", "count": 220 }],
    "trend_daily": [{ "date": "2026-07-01", "count": 40 }],
    "model": {
      "prediction_run_id": "...",
      "model_version": "risk_lgbm@2026.07.20",
      "generated_at": "...",
      "is_stale": false
    }
  }
}
```

#### Models
- `KpiSet` — numeric tiles + deltas  
- `NamedCount` — `{ name|id, count }`  
- `DailyCount` — `{ date, count }`  
- `ModelPointer` — current model metadata for trust UI  

---

### 4.2 `GET /dashboard/alerts`

Operational callouts (threshold anomalies).

**Response:** `{ "data": DashboardAlert[] }`

#### `DashboardAlert`
| Field | Type |
|-------|------|
| `id` | string |
| `severity` | `info` \| `warning` \| `critical` |
| `title` | string |
| `body` | string |
| `district_id` | uuid \| null |
| `station_id` | uuid \| null |
| `metric` | string |
| `value` | number |
| `baseline` | number \| null |
| `href` | string \| null | deep link path |

---

### 4.3 `GET /dashboard/map-summary`

Compact side-panel for map home: top hotspots + risk stations.

**Response:**

```json
{
  "data": {
    "top_hotspots": [ { "id": "...", "rank": 1, "score": 0.92, "centroid": {"lon":0,"lat":0}, "incident_count": 40 } ],
    "top_risk_stations": [ { "station_id": "...", "name": "...", "risk_score": 0.81 } ]
  }
}
```

---

## 5. Analytics APIs

Base: `/api/v1/analytics`  
Permission: `analytics:read`  
Heavier than dashboard; powers Analytics page / ECharts.

### 5.1 `GET /analytics/trends`

**Query:** scope + `interval=day|week|month` + offense filters  
**Response `TrendResponse`**

```json
{
  "data": {
    "interval": "day",
    "series": [
      {
        "key": "all",
        "points": [{ "bucket_start": "...", "count": 12 }]
      }
    ]
  }
}
```

#### `TrendSeries` / `TrendPoint`

---

### 5.2 `GET /analytics/breakdown`

**Query:** `group_by=offense|severity|station|hour_of_day|day_of_week`  
**Response:** `{ "data": { "group_by": "...", "items": NamedCount[] } }`

---

### 5.3 `GET /analytics/compare`

Compare two scopes or two time ranges.

**Request via query `CompareQuery`**

| Param | Notes |
|-------|-------|
| `mode` | `time` \| `place` |
| `a_from`,`a_to` / `b_from`,`b_to` | time mode |
| `a_district_id`,`b_district_id` | place mode |

**Response `CompareResponse`**

```json
{
  "data": {
    "a": { "label": "...", "total": 100, "by_offense": [] },
    "b": { "label": "...", "total": 130, "by_offense": [] },
    "delta_pct": 30.0
  }
}
```

---

### 5.4 `GET /analytics/time-heatmap`

Hour × weekday matrix for control-room patterns.

**Response:**

```json
{
  "data": {
    "matrix": [[0,1,2],[...]],
    "x_labels": ["Mon","Tue", "..."],
    "y_labels": ["0","1", "...","23"]
  }
}
```

---

### 5.5 `GET /analytics/export`

**Query:** same filters as trends + `format=csv|json`  
**Response:** file download (`text/csv` or JSON)  
Permission: `analytics:export`  
Audited as `export`.

---

### 5.6 Socio-economic correlation APIs

Base: `/api/v1/analytics/socio-economic`  
Permission: `analytics:read`  
Closes the datathon gap: **socio-economic crime correlation**.

#### `GET /analytics/socio-economic/indicators`

List indicator values (AuthZ-scoped by district).

**Query**

| Param | Type | Notes |
|-------|------|-------|
| `year` | int | default latest available |
| `district_id` | uuid | optional filter |
| `indicator_code` | string | optional |

**Response**

```json
{
  "data": [
    {
      "district_id": "...",
      "district_code": "BLR",
      "district_name": "Bengaluru City",
      "year": 2024,
      "indicator_code": "unemployment_rate",
      "value": 7.2,
      "unit": "%",
      "source": "demo-seed"
    }
  ]
}
```

#### `GET /analytics/socio-economic/crime-metrics`

Yearly district crime intensity used for correlation.

**Query:** `year`, `district_id`  
**Response:** `{ "data": DistrictCrimeMetric[] }`

#### `GET /analytics/socio-economic/correlation`

Pearson correlation between one socio indicator and a crime metric across districts.

**Query**

| Param | Type | Default |
|-------|------|---------|
| `year` | int | latest |
| `indicator_code` | string | required |
| `crime_metric` | `crime_rate_per_100k` \| `incident_count` | `crime_rate_per_100k` |

**Response `CorrelationResult`**

```json
{
  "data": {
    "year": 2024,
    "indicator_code": "unemployment_rate",
    "crime_metric": "crime_rate_per_100k",
    "method": "pearson",
    "coefficient": 0.71,
    "abs_coefficient": 0.71,
    "sample_size": 8,
    "interpretation": "strong_positive",
    "points": [
      {
        "district_id": "...",
        "district_code": "BLR",
        "district_name": "Bengaluru City",
        "indicator_value": 7.2,
        "crime_value": 312.5
      }
    ]
  }
}
```

#### `GET /analytics/socio-economic/correlations`

Rank all indicators by \|r\| for a year (leaderboard for dashboards).

**Query:** `year`, `crime_metric`  
**Response:** `{ "data": CorrelationSummary[] }` sorted by `abs_coefficient` desc.

---

## 6. Prediction APIs

Base: `/api/v1/predictions`  
Permission: `prediction:read`  
Serving **precomputed** runs from DB (batch ML).

### 6.1 `GET /predictions/runs`

List prediction runs (current + history).

**Query:** `task`, `metric`, `scope_type`, `is_current`, `district_id`  
**Response:** `{ "data": PredictionRunSummary[] }`

#### `PredictionRunSummary`
| Field | Type |
|-------|------|
| `id` | uuid |
| `model_code` | string |
| `model_version` | string |
| `task` | enum |
| `metric` | enum |
| `scope_type` | enum |
| `horizon_start` / `horizon_end` | datetime |
| `generated_at` | datetime |
| `is_current` | boolean |
| `status_banner` | `"fresh"` \| `"stale"` \| `"shadow"` |

---

### 6.2 `GET /predictions/runs/{run_id}`

Run detail + model card pointer.

**Response `PredictionRunDetail`** includes `metrics`, `feature_list`, `artifact` metadata.

---

### 6.3 `GET /predictions/runs/{run_id}/values`

Paged prediction values for maps/tables.

**Query:** `district_id`, `station_id`, `occurs_on`, `min_value`, `limit`, `cursor`  
**Response:** `{ "data": PredictionValue[], "page": ... }`

#### `PredictionValue`
| Field | Type |
|-------|------|
| `id` | uuid |
| `scope` | `{ type, district_id?, station_id?, grid_cell_id?, hotspot_feature_id? }` |
| `value` | number |
| `lower_bound` / `upper_bound` | number \| null |
| `occurs_on` | date \| null |
| `properties` | object |

---

### 6.4 `GET /predictions/current`

Convenience: current production run + top values for a scope.

**Query:** `metric=risk_score|incident_count`, `district_id`, `station_id`, `top_n`  
**Response:**

```json
{
  "data": {
    "run": { /* PredictionRunSummary */ },
    "values": [ /* PredictionValue */ ]
  }
}
```

---

### 6.5 `GET /predictions/values/{value_id}/explanation`

Explainable AI payload (SHAP).

**Response `ExplanationResponse`**

```json
{
  "data": {
    "prediction_value_id": "...",
    "model_version": "risk_lgbm@2026.07.20",
    "base_value": 0.42,
    "output_value": 0.81,
    "global_importance": [
      { "feature": "lag_7d_count", "importance": 0.22 }
    ],
    "local_contributions": [
      { "feature": "lag_7d_count", "value": 18, "contribution": 0.15 }
    ],
    "summary_text": "Risk elevated primarily due to 7-day incident lag and weekend peak."
  }
}
```

#### Models
- `FeatureImportance` — `{ feature, importance }`  
- `FeatureContribution` — `{ feature, value, contribution }`  

**Errors:** `404 EXPLANATION_UNAVAILABLE` if artifact missing (UI must handle).

---

### 6.6 `GET /predictions/hotspots/current`

Current hotspot run features (JSON + optional GeoJSON via spatial layer).

**Query:** `district_id`, `limit`  
**Response:** `{ "data": { "run": HotspotRunSummary, "features": HotspotFeature[] } }`

#### `HotspotFeature`
| Field | Type |
|-------|------|
| `id` | uuid |
| `rank` | integer |
| `score` | number |
| `incident_count` | integer |
| `centroid` | `GeoPoint` |
| `properties` | object |

Geo shapes: `GET /spatial/layers/hotspots_current`.

---

### 6.7 `GET /predictions/models`

Model registry listing (analyst/admin).

**Response:** `{ "data": ModelCard[] }`

#### `ModelCard`
| Field | Type |
|-------|------|
| `model_code` | string |
| `model_version` | string |
| `task` | enum |
| `algorithm` | string |
| `status` | enum |
| `metrics` | object |
| `train_window` | `{ start, end }` \| null |

---

## 7. Network APIs

Base: `/api/v1/network`  
Permission: `network:read`

### 7.1 `GET /network/graph`

Criminal network subgraph for Cytoscape.

**Query `NetworkGraphQuery`**

| Param | Notes |
|-------|-------|
| `person_id` | ego network center (optional) |
| `district_id` / `station_id` | spatial filter via related incidents |
| `from` / `to` | incident window for derived edges |
| `link_types` | enum[] |
| `min_weight` | number |
| `depth` | 1–2 |
| `limit_nodes` | cap |

**Response `NetworkGraphResponse`**

```json
{
  "data": {
    "nodes": [
      {
        "id": "person-uuid",
        "label": "Name",
        "is_repeat_offender": true,
        "incident_count": 5,
        "risk_flags": {}
      }
    ],
    "edges": [
      {
        "id": "link-uuid",
        "source": "person-a",
        "target": "person-b",
        "link_type": "co_accused",
        "origin": "derived",
        "weight": 3.0
      }
    ],
    "meta": { "truncated": false, "node_count": 40, "edge_count": 55 }
  }
}
```

#### Models: `NetworkNode`, `NetworkEdge`, `GraphMeta`

---

### 7.2 `GET /network/persons/{person_id}`

Person profile for inspector panel.

**Response `PersonDetail`**

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `full_name` | string | |
| `alias` | string \| null | |
| `is_repeat_offender` | boolean | |
| `incident_count` | integer | |
| `incidents` | `IncidentSummary[]` | recent capped |
| `links_out_count` | integer | |
| sensitive fields | | permission-gated |

---

### 7.3 `GET /network/repeat-offenders`

Ranked list.

**Query:** scope + `from`/`to` + `limit`  
**Response:** `{ "data": RepeatOffenderRow[] }`

#### `RepeatOffenderRow`
| Field | Type |
|-------|------|
| `person_id` | uuid |
| `full_name` | string |
| `incident_count` | integer |
| `offense_mix` | NamedCount[] |
| `last_occurred_at` | datetime |
| `score` | number | heuristic/model |

---

### 7.4 `GET /network/links/{link_id}`

Edge evidence detail (`evidence_incident_id`, properties).

---

## 8. AI APIs

Base: `/api/v1/ai`  
Permission: `ai:chat`  
Tools inherit **same AuthContext** (no privilege escalation).

### 8.1 `POST /ai/chat` (SSE)

Streaming copilot turn.

**Request `AiChatRequest`**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `conversation_id` | uuid | no | Create if omitted |
| `message` | string | yes | user text |
| `district_id` | uuid | no | Active scope hint (still AuthZ-checked) |
| `station_id` | uuid | no | |
| `mode` | `"ask"` \| `"brief"` \| `"explain"` | no | default `ask` |

**Response:** `text/event-stream`

Event types:
| Event | Data payload |
|-------|----------------|
| `conversation` | `{ conversation_id }` |
| `token` | `{ text }` |
| `citation` | `{ type, id, label, href? }` |
| `tool_start` | `{ tool_name }` |
| `tool_end` | `{ tool_name, status }` |
| `error` | standard error object |
| `done` | `{ message_id, finish_reason }` |

Non-stream fallback (design optional): `POST /ai/chat/sync` → `AiChatSyncResponse`.

#### `AiChatSyncResponse`
| Field | Type |
|-------|------|
| `conversation_id` | uuid |
| `message_id` | uuid |
| `content` | string |
| `citations` | `Citation[]` |
| `tool_traces` | `ToolTraceSummary[]` |

#### `Citation`
| Field | Type |
|-------|------|
| `type` | `incident` \| `prediction` \| `hotspot` \| `document` \| `analytics` |
| `id` | string |
| `label` | string |

#### `ToolTraceSummary`
| Field | Type |
|-------|------|
| `tool_name` | string |
| `status` | `ok` \| `error` \| `denied` |
| `latency_ms` | number \| null |

---

### 8.2 `GET /ai/conversations`

List current user’s conversations.

**Response:** `{ "data": ConversationSummary[] }`  
`ConversationSummary`: `id`, `title`, `updated_at`, `district_id`

---

### 8.3 `GET /ai/conversations/{conversation_id}`

Messages + light traces.

**Response:** `{ "data": { "conversation": ..., "messages": Message[] } }`

#### `Message`
| Field | Type |
|-------|------|
| `id` | uuid |
| `role` | enum |
| `content` | string |
| `citations` | Citation[] |
| `created_at` | datetime |

---

### 8.4 `DELETE /ai/conversations/{conversation_id}`

Soft/hard delete per policy — `204`.

---

### 8.5 `POST /ai/briefs/generate`

Generate command brief for a scope/window (async-capable).

**Request `BriefGenerateRequest`**

| Field | Type |
|-------|------|
| `district_id` | uuid |
| `from` / `to` | datetime |
| `include_predictions` | boolean |
| `include_hotspots` | boolean |
| `include_network_highlights` | boolean |

**Response `202`:** `{ "data": { "job_id": "...", "brief_id": "..." } }`  
**Or `200` sync:** `{ "data": BriefDocument }`

#### `BriefDocument`
| Field | Type |
|-------|------|
| `id` | uuid |
| `title` | string |
| `markdown` | string |
| `citations` | Citation[] |
| `generated_at` | datetime |
| `model` | string |

---

### 8.6 `GET /ai/briefs/{brief_id}`

Fetch generated brief.

---

## 9. Decision support (related; included for completeness)

Base: `/api/v1/decision`  
Permission: `decision:read` / `decision:approve`

### 9.1 `POST /decision/patrol-plans/recommend`

**Request:** `{ district_id, horizon_start, horizon_end, max_items }`  
**Response:** `PatrolPlan` with `items[]` ranked + explanations.

### 9.2 `GET /decision/patrol-plans/{id}`

### 9.3 `POST /decision/patrol-plans/{id}/approve`  
Body: `{ note? }` — human-in-the-loop.

---

## 10. Health (ops)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/api/v1/health/live` | no | `{ "status": "ok" }` |
| GET | `/api/v1/health/ready` | no | checks DB/Redis; `503` if not ready |

---

## 11. Endpoint catalog (quick index)

| Area | Method | Path |
|------|--------|------|
| Auth | POST | `/auth/login` |
| Auth | POST | `/auth/refresh` |
| Auth | POST | `/auth/logout` |
| Auth | GET | `/auth/me` |
| Org | GET | `/org/districts` |
| Org | GET | `/org/districts/{id}` |
| Org | GET | `/org/stations` |
| Org | GET | `/org/stations/{id}` |
| Crime | GET | `/incidents` |
| Crime | GET | `/incidents/{id}` |
| Crime | POST | `/incidents/ingest` |
| Crime | GET | `/incidents/ingest/batches/{id}` |
| Crime | GET | `/offense-types` |
| Spatial | GET | `/spatial/incidents` |
| Spatial | GET | `/spatial/layers/{layer_key}` |
| Spatial | GET | `/spatial/radius` |
| Dashboard | GET | `/dashboard/overview` |
| Dashboard | GET | `/dashboard/alerts` |
| Dashboard | GET | `/dashboard/map-summary` |
| Analytics | GET | `/analytics/trends` |
| Analytics | GET | `/analytics/breakdown` |
| Analytics | GET | `/analytics/compare` |
| Analytics | GET | `/analytics/time-heatmap` |
| Analytics | GET | `/analytics/export` |
| Analytics | GET | `/analytics/socio-economic/indicators` |
| Analytics | GET | `/analytics/socio-economic/crime-metrics` |
| Analytics | GET | `/analytics/socio-economic/correlation` |
| Analytics | GET | `/analytics/socio-economic/correlations` |
| Prediction | GET | `/predictions/runs` |
| Prediction | GET | `/predictions/runs/{id}` |
| Prediction | GET | `/predictions/runs/{id}/values` |
| Prediction | GET | `/predictions/current` |
| Prediction | GET | `/predictions/values/{id}/explanation` |
| Prediction | GET | `/predictions/hotspots/current` |
| Prediction | GET | `/predictions/models` |
| Network | GET | `/network/graph` |
| Network | GET | `/network/persons/{id}` |
| Network | GET | `/network/repeat-offenders` |
| Network | GET | `/network/links/{id}` |
| AI | POST | `/ai/chat` (SSE) |
| AI | GET | `/ai/conversations` |
| AI | GET | `/ai/conversations/{id}` |
| AI | DELETE | `/ai/conversations/{id}` |
| AI | POST | `/ai/briefs/generate` |
| AI | GET | `/ai/briefs/{id}` |
| Decision | POST | `/decision/patrol-plans/recommend` |
| Decision | GET | `/decision/patrol-plans/{id}` |
| Decision | POST | `/decision/patrol-plans/{id}/approve` |
| Health | GET | `/health/live` |
| Health | GET | `/health/ready` |

---

## 12. Permission matrix (API → permission)

| Permission | Endpoints |
|------------|-----------|
| (public) | health |
| authenticated | `/auth/me`, logout/refresh |
| `incident:read` | incidents + spatial reads |
| `incident:ingest` | ingest |
| `analytics:read` | dashboard + analytics |
| `analytics:export` | export |
| `prediction:read` | predictions + explanations + hotspots |
| `network:read` | network/* |
| `ai:chat` | ai/chat + conversations |
| `ai:brief` | briefs |
| `decision:read` | get plans / recommend |
| `decision:approve` | approve |

---

## 13. Design decisions

1. **Dashboard vs Analytics split** — keeps home screen fast/cacheable; analytics carries heavy group-bys.  
2. **GeoJSON raw for map endpoints** — MapLibre/deck.gl native; tabular incidents stay enveloped.  
3. **Predictions are read APIs** — training/scoring is worker/ML plane, not REST train endpoints.  
4. **Explanations are separate GETs** — avoid bloating value list payloads.  
5. **AI is SSE-first** — better UX; sync optional.  
6. **AuthZ always server-side** — client scope params are hints/filters, never authority.  
7. **404 over 403 for hidden resources** — reduce jurisdiction enumeration (configurable per deployment).

---

## 14. Out of scope (this phase)

- FastAPI routers / Pydantic classes as code  
- OpenAPI YAML generation committed as artifact (next optional step)  
- Client SDK implementation  

---

## Approval gate

Confirm or amend endpoint set, envelopes, and model shapes.

**STOP — awaiting approval before next design phase (UI screen inventory, ML model cards, or threat model).**
