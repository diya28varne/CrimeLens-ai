# CrimeLens AI — Complete Folder & File Structure

**Status:** Scaffold created on disk (placeholders only — no implementation code)  
**Architecture baseline:** 2026 revised SAD (modular monolith, MapLibre, pgvector, PydanticAI, OpenAPI codegen)

This document explains **every folder** and **every planned / present file**, and **why it exists**.

---

## Design rules encoded in this tree

1. `apps/` = deployable user apps only  
2. `services/` = deployable backend runtimes  
3. `packages/` = shared libraries (no HTTP servers)  
4. `toolings/` = engineering standards (lint/tsconfig), not product logic  
5. `infra/` = how it runs  
6. `docs/` = why it exists  
7. `data/` = datasets and boundaries (not code)  
8. `scripts/` = human/CI operational entrypoints  

---

## Root

```text
CrimeLens-ai/
├── .github/
├── apps/
├── services/
├── packages/
├── toolings/
├── infra/
├── docs/
├── scripts/
├── data/
├── .env.example
├── .gitignore
├── .nvmrc
├── .python-version
├── LICENSE
├── Makefile
├── README.md
├── docker-compose.yml
├── package.json
├── pnpm-workspace.yaml
├── pyproject.toml
└── turbo.json
```

| Path | Why it exists |
|------|----------------|
| `README.md` | Repo entrypoint for humans/judges; points to architecture docs |
| `LICENSE` | Legal posture placeholder for datathon/agency terms |
| `.gitignore` | Keeps secrets, caches, generated clients, ML artifacts out of git |
| `.env.example` | Documents required env vars without committing secrets |
| `.nvmrc` | Pins Node major for frontend tooling consistency |
| `.python-version` | Pins Python for uv/pyenv consistency |
| `package.json` | Root JS workspace scripts (`dev/build/lint/typecheck/test`) |
| `pnpm-workspace.yaml` | Declares pnpm workspace package globs |
| `turbo.json` | Turborepo task graph / cache policy |
| `pyproject.toml` | uv workspace root for Python members |
| `docker-compose.yml` | Local multi-service topology (api/worker/db/redis) |
| `Makefile` | Thin facade for common demo/bootstrap commands |

---

## `.github/` — CI/CD & collaboration

```text
.github/
├── workflows/
│   ├── ci.yml
│   └── cd-staging.yml
└── ISSUE_TEMPLATE/
```

| Path | Why |
|------|-----|
| `.github/workflows/` | GitHub Actions definitions |
| `ci.yml` | PR gate: lint, typecheck, unit tests, build |
| `cd-staging.yml` | Deploy staging on approved main merges |
| `ISSUE_TEMPLATE/` | Standardize bug/feature intake for team process |

---

## `apps/` — Deployable frontend applications

Only user-facing apps live here. Backend never goes under `apps/`.

### `apps/web/` — Next.js command console

```text
apps/web/
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
├── components.json
├── public/
│   ├── icons/
│   └── geo/
├── src/
│   ├── middleware.ts          (planned)
│   ├── app/
│   ├── features/
│   ├── entities/
│   ├── widgets/
│   ├── shared/
│   └── styles/
└── tests/
    ├── e2e/
    └── unit/
```

#### App package config files

| File | Why |
|------|-----|
| `package.json` | `@crimelens/web` package manifest & scripts |
| `tsconfig.json` | Strict TS config; extends shared base |
| `next.config.ts` | Next.js build/runtime configuration |
| `postcss.config.mjs` | Tailwind v4 / PostCSS pipeline |
| `components.json` | shadcn/ui generator settings |

#### `public/`

| Folder | Why |
|--------|-----|
| `public/icons/` | Static brand/UI icons served as-is |
| `public/geo/` | Static GeoJSON (district outlines for offline demo fallback) |

#### `src/app/` — Next.js App Router (routes only)

Route files orchestrate layouts and compose features. **No business rules here.**

| Path | Why |
|------|-----|
| `src/app/layout.tsx` | Root HTML shell, fonts, theme providers |
| `src/app/page.tsx` | `/` redirect to login or dashboard |
| `src/app/globals.css` | Global styles / CSS variable tokens entry |
| `(auth)/login/` | Unauthenticated login route group |
| `(app)/dashboard/` | Authenticated dashboard page |
| `(app)/analytics/` | Analytics page |
| `(app)/map/` | Crime map page |
| `(app)/prediction/` | Prediction + SHAP page |
| `(app)/network/` | Criminal network page |
| `(app)/reports/` | Reports page |
| `(app)/ai/` | AI copilot page |
| `(app)/settings/` | User/settings page |
| `(app)/admin/` | Admin page |
| `api/health/` | Optional Next-side health/proxy probe for hosting |

Route groups `(auth)` and `(app)` exist to apply different layouts (public vs shell) without affecting URL paths.

#### `src/features/` — Feature-based modules

Each feature owns its UI slices, hooks, and view-models for one product capability.

| Feature folder | Why |
|----------------|-----|
| `features/auth/` | Login forms, session hooks, auth guards UI |
| `features/dashboard/` | KPI tiles, overview widgets composition |
| `features/analytics/` | Trend filters, breakdown panels |
| `features/map/` | MapLibre/deck.gl layer controls, filters, legend |
| `features/prediction/` | Forecast views + explanation consumer UI |
| `features/network/` | Cytoscape graph controls and inspectors |
| `features/reports/` | Report builders / export actions |
| `features/ai-copilot/` | Chat UI using Vercel AI SDK stream consumer |
| `features/settings/` | Preferences, theme, jurisdiction defaults |
| `features/admin/` | User/role/job admin screens |

**Planned files per feature (pattern, not all created as code):**

| File pattern | Why |
|--------------|-----|
| `index.ts` | Public exports for the feature |
| `*.tsx` components | Feature-local presentational/interactive UI |
| `hooks/*.ts` | TanStack Query hooks / local UI state hooks |
| `schema.ts` | Zod schemas for feature forms/filters |
| `types.ts` | Feature-local TS types (non-contract) |

#### `src/entities/` — UI-domain entity helpers

| Entity | Why |
|--------|-----|
| `entities/incident/` | Incident labeling, status badges, formatters |
| `entities/station/` | Station display helpers |
| `entities/prediction/` | Prediction/model_version display helpers |
| `entities/person/` | Person/network node display helpers |

Entities are **not** API clients; they are UI-facing domain representations.

#### `src/widgets/` — Reusable composed shells

| Widget | Why |
|--------|-----|
| `widgets/app-shell/` | Sidebar, topbar, jurisdiction switcher layout |
| `widgets/map-viewport/` | Shared MapLibre + deck.gl viewport container |
| `widgets/chart-panel/` | Shared ECharts panel wrapper |
| `widgets/explanation-panel/` | Shared SHAP/explanation side panel |

Widgets compose features/entities; they still contain **no backend business logic**.

#### `src/shared/` — Cross-feature primitives

| Path | Why |
|------|-----|
| `shared/ui/` | shadcn primitives & design-system components |
| `shared/lib/` | Pure utilities (dates, number format, cn, etc.) |
| `shared/hooks/` | Generic hooks (debounce, media query) |
| `shared/config/` | Public env, feature flags, route constants |
| `shared/api/` | API client wrappers |
| `shared/api/generated/` | **Generated** OpenAPI TS client (gitignored outputs) |

#### `src/styles/`

Design tokens / theme CSS modules beyond `globals.css`.

#### `src/middleware.ts` (planned)

Edge/auth gate and security headers only — never domain rules.

#### `tests/`

| Path | Why |
|------|-----|
| `tests/unit/` | Vitest/Jest unit tests for hooks/utils |
| `tests/e2e/` | Playwright flows for critical journeys |

---

## `packages/` — Shared libraries

### `packages/py-domain/` — Shared Python domain/application core

Used by `api`, `worker`, and (selectively) `ml` so business rules are not copied.

```text
packages/py-domain/
├── pyproject.toml
├── crimelens_domain/
│   ├── identity/
│   ├── org/
│   ├── incidents/
│   ├── spatial/
│   ├── analytics/
│   ├── predictions/
│   ├── network/
│   ├── decision/
│   ├── ai_copilot/
│   ├── audit/
│   ├── jobs/
│   └── shared/
└── tests/
```

| Path | Why |
|------|-----|
| `pyproject.toml` | Package manifest for `crimelens-domain` |
| `identity/` | AuthContext, roles/permissions policies |
| `org/` | District/station/jurisdiction domain types & rules |
| `incidents/` | Incident entities, invariants, offense classification rules |
| `spatial/` | Spatial query ports / DTO shapes (not SQL) |
| `analytics/` | Metric definitions / aggregation contracts |
| `predictions/` | Prediction entities, model_version rules |
| `network/` | Graph edge semantics, repeat-offender rules |
| `decision/` | Patrol recommendation domain logic |
| `ai_copilot/` | Agent ports, tool allowlists, grounding policies |
| `audit/` | Audit event types & required fields |
| `jobs/` | Job names, payloads, idempotency keys |
| `shared/` | Result types, errors, time/CRS helpers |
| `tests/` | Domain unit tests (pure, no FastAPI) |

**Planned files per domain module:**

| File | Why |
|------|-----|
| `__init__.py` | Package marker |
| `entities.py` / `models.py` | Domain entities/value objects |
| `policies.py` | Authorization & invariant policies |
| `ports.py` | Repository/service interfaces (Dependency Inversion) |
| `services.py` | Application/domain services (use cases) |

### `packages/web-ui/` — Optional shared UI package

| Path | Why |
|------|-----|
| `package.json` | `@crimelens/web-ui` manifest |
| `src/components/` | Truly cross-app UI (only if a second web app appears) |
| `src/tokens/` | Shared design tokens exportable beyond `apps/web` |

Exists to prevent premature dumping of everything into `apps/web`, while remaining optional for datathon (may stay thin).

---

## `toolings/` — Engineering standards

| Path | Why |
|------|-----|
| `toolings/typescript/base.json` | Shared strict TSConfig base |
| `toolings/eslint/base.js` | Shared ESLint flat config |
| `toolings/prettier/prettierrc.json` | Shared formatting rules |

Keeps style/type tooling out of product packages (maintainability).

---

## `services/` — Deployable backend runtimes

### `services/api/` — FastAPI modular monolith

```text
services/api/
├── pyproject.toml
├── alembic.ini
├── alembic/versions/
├── openapi/
├── app/
│   ├── main.py              (planned)
│   ├── deps.py              (planned)
│   ├── core/
│   ├── middleware/
│   ├── modules/
│   └── infra/
└── tests/
    ├── unit/
    └── integration/
```

| Path | Why |
|------|-----|
| `pyproject.toml` | API package deps & scripts |
| `alembic.ini` | Migration runner config |
| `alembic/versions/` | Versioned SQL schema migrations |
| `openapi/` | Exported OpenAPI snapshots for codegen/CI drift checks |
| `app/main.py` | Composition root (app factory, router include, lifespan) |
| `app/deps.py` | FastAPI Depends providers (DB, AuthContext, repos) |
| `app/core/` | Settings, logging, security helpers, constants |
| `app/middleware/` | Request ID, timing, rate limit, security headers |
| `app/modules/*/` | Interface adapters per bounded context |
| `app/infra/` | Infrastructure adapters (DB/Redis/vector/LLM/storage) |
| `tests/unit/` | Fast router/service tests with fakes |
| `tests/integration/` | DB/Redis-backed tests |

#### `app/modules/<context>/` planned files

| File | Why |
|------|-----|
| `router.py` | HTTP endpoints for the context |
| `schemas.py` | Pydantic request/response models |
| `dependencies.py` | Module-local DI wiring |
| `presenter.py` (optional) | Map domain → API schema |

Business orchestration should call into `packages/py-domain`, not re-implement rules.

#### Module folders

| Module | Why |
|--------|-----|
| `identity/` | Auth login/refresh/me |
| `org/` | Districts/stations |
| `incidents/` | Incident search/ingest status |
| `spatial/` | BBox/radius/layers/GeoJSON |
| `analytics/` | KPI/trends/comparisons |
| `predictions/` | Prediction reads + explanations |
| `network/` | Graph + repeat offenders |
| `decision/` | Patrol plan recommendations |
| `ai/` | Copilot SSE/chat endpoints |
| `admin/` | Users, jobs, audit export |
| `health/` | Liveness/readiness |

#### `app/infra/` adapters

| Adapter | Why |
|---------|-----|
| `infra/db/` | SQLAlchemy engine/session, GeoAlchemy mappings |
| `infra/redis/` | Cache, rate-limit, Taskiq broker helpers |
| `infra/vector/` | pgvector implementation of VectorStore port |
| `infra/llm/` | Gemini + PydanticAI runner adapters |
| `infra/storage/` | Artifact/object storage for SHAP/model files |

---

### `services/worker/` — Async job runtime

```text
services/worker/
├── pyproject.toml
├── app/
│   └── main.py              (planned)
└── tests/
```

| Path | Why |
|------|-----|
| `pyproject.toml` | Worker package (depends on domain + shared infra) |
| `app/main.py` | Taskiq worker process entrypoint |
| `tests/` | Job handler tests |

**Why separate from API:** request latency isolation.  
**Why same domain package:** DRY — no duplicated business logic.

Planned responsibilities: aggregate refresh, cache warming, embedding upsert, report generation, post-ingest hooks.

---

### `services/ml/` — Offline ML plane

```text
services/ml/
├── pyproject.toml
├── configs/
├── pipelines/
│   ├── features/
│   ├── train/
│   ├── score/
│   ├── explain/
│   ├── hotspot/
│   ├── forecast/
│   └── run_all.md
├── src/crimelens_ml/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── eval/
│   └── registry/
├── artifacts/          (gitignored outputs)
├── notebooks/
└── tests/
```

| Path | Why |
|------|-----|
| `pyproject.toml` | ML tooling deps (Polars, LightGBM, SHAP, Nixtla, GeoPandas) |
| `configs/` | YAML/TOML model configs (horizons, grids, feature sets) |
| `pipelines/features/` | Feature build jobs |
| `pipelines/train/` | Training jobs |
| `pipelines/score/` | Batch scoring jobs |
| `pipelines/explain/` | SHAP artifact generation |
| `pipelines/hotspot/` | HDBSCAN / density hotspot jobs |
| `pipelines/forecast/` | Forecast/risk scoring jobs |
| `pipelines/run_all.md` | Ordered pipeline orchestration notes |
| `src/crimelens_ml/data/` | Extract/load helpers from PostGIS |
| `src/crimelens_ml/features/` | Feature engineering transforms |
| `src/crimelens_ml/models/` | Model wrappers (LGBM/XGB/Nixtla) |
| `src/crimelens_ml/eval/` | Metrics & time-split evaluation |
| `src/crimelens_ml/registry/` | Write model_registry / promotion helpers |
| `artifacts/` | Local model binaries / SHAP values (not committed) |
| `notebooks/` | Exploratory analysis only (not production path) |
| `tests/` | Pipeline unit tests with sample frames |

---

## `infra/` — Runtime packaging & observability

```text
infra/
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── Dockerfile.web
│   └── Dockerfile.ml
├── observability/
│   ├── otel/otel-collector.yaml
│   ├── prometheus/prometheus.yml
│   └── grafana/
│       ├── dashboards/
│       └── provisioning/
├── railway/
└── vercel/
```

| Path | Why |
|------|-----|
| `Dockerfile.api` | API container image definition |
| `Dockerfile.worker` | Worker container image |
| `Dockerfile.web` | Optional web image (non-Vercel path) |
| `Dockerfile.ml` | Batch ML job image |
| `otel/otel-collector.yaml` | OpenTelemetry collector (hackathon/S1) |
| `prometheus/prometheus.yml` | Scrape config (staged profile) |
| `grafana/dashboards/` | Dashboard JSON definitions |
| `grafana/provisioning/` | Grafana datasource/dashboard provisioning |
| `railway/` | Railway service config notes/templates |
| `vercel/` | Vercel project config notes/templates |

---

## `docs/` — Knowledge plane

| Path | Why |
|------|-----|
| `architecture/` | SAD, C4, folder structure (this doc) |
| `adr/` | Architecture Decision Records |
| `ADR-0001` … `ADR-0005` | Locked 2026 decisions |
| `domain/` | Ubiquitous language & bounded contexts |
| `product/` | Personas & MVP scope |
| `api/` | API versioning & contract policies |
| `ml/` | Model governance |
| `gis/` | Spatial standards |
| `security/` | Threat model |
| `runbooks/` | Local demo & incident response |

Docs exist so decisions survive demos and team changes.

---

## `scripts/` — Operational entrypoints

| Path | Why |
|------|-----|
| `scripts/bootstrap.md` | Dev machine bring-up checklist |
| `scripts/generate-client.md` | OpenAPI → TS client generation procedure |

Later implementation may add `bootstrap.sh` / `bootstrap.ps1`; markdown exists now as the contract for those scripts.

---

## `data/` — Datasets (not application code)

| Path | Why |
|------|-----|
| `data/samples/` | Small anonymized samples for UI/API tests |
| `data/seeds/` | Deterministic seed datasets for demos |
| `data/boundaries/` | District/station polygon sources |
| `data/.cache/` | Local processing cache (gitignored) |

---

## Planned source files (not implemented yet)

These are **required by architecture** and currently represented by `.purpose.md` stubs or empty dirs:

### Frontend planned files

| File | Why |
|------|-----|
| `apps/web/src/app/layout.tsx` | Root layout |
| `apps/web/src/app/page.tsx` | Root redirect |
| `apps/web/src/app/globals.css` | Global styles |
| `apps/web/src/middleware.ts` | Auth/session gate |
| `apps/web/src/app/(auth)/login/page.tsx` | Login screen route |
| `apps/web/src/app/(app)/layout.tsx` | Authenticated shell layout |
| `apps/web/src/app/(app)/*/page.tsx` | One page per feature route |
| `apps/web/src/shared/api/client.ts` | Thin wrapper over generated client |
| `apps/web/src/shared/api/generated/*` | Codegen output |

### Backend planned files (per module pattern)

| File | Why |
|------|-----|
| `services/api/app/main.py` | App factory |
| `services/api/app/deps.py` | DI |
| `services/api/app/core/settings.py` | Env settings (Pydantic Settings) |
| `services/api/app/core/logging.py` | Structured logging |
| `services/api/app/core/security.py` | Password/JWT/cookie helpers |
| `services/api/app/middleware/*.py` | Cross-cutting HTTP middleware |
| `services/api/app/modules/*/router.py` | HTTP routes |
| `services/api/app/modules/*/schemas.py` | API schemas |
| `services/api/app/infra/db/session.py` | DB session factory |
| `services/api/app/infra/db/models.py` or `models/` | ORM models |
| `services/worker/app/main.py` | Worker entry |
| `services/worker/app/tasks/*.py` | Taskiq tasks |

### Domain planned files

| File | Why |
|------|-----|
| `packages/py-domain/crimelens_domain/*/ports.py` | Interfaces |
| `packages/py-domain/crimelens_domain/*/services.py` | Use cases |
| `packages/py-domain/crimelens_domain/*/policies.py` | AuthZ & invariants |

### ML planned files

| File | Why |
|------|-----|
| `services/ml/configs/*.yaml` | Model/feature configs |
| `services/ml/pipelines/**/main.py` | Job CLIs |
| `services/ml/src/crimelens_ml/**/*.py` | Library code for pipelines |

---

## `.gitkeep` files

Present in empty directories so Git tracks the tree before implementation. They have **no runtime meaning** and are removed naturally when real files arrive.

---

## Dependency direction (enforced by folders)

```text
apps/web ──HTTP──► services/api ──uses──► packages/py-domain
services/worker ──uses──► packages/py-domain (+ api infra adapters as needed)
services/ml ──reads/writes DB──► Postgres; may import shared types carefully
toolings ──used by──► apps/web, packages/web-ui
infra ──packages──► services/*, apps/web
```

**Forbidden by structure:**
- `apps/web` importing Python  
- `packages/py-domain` importing FastAPI routers  
- `services/ml` importing Next.js  
- Business rules living in `app/modules/*/router.py` or React components  

---

## What was intentionally NOT created

- No React components with UI logic  
- No FastAPI routers/endpoints  
- No SQL migrations with tables  
- No trained models  
- No real secrets  
- No Qdrant service folder (deferred by ADR-0002)  
- No Leaflet folders (replaced by MapLibre in feature/map + map-viewport widget)

---

## Scaffold status

On-disk skeleton created with:
- Empty directory tree + `.gitkeep`
- Root/workspace config placeholders
- ADR & docs stubs
- Purpose stubs for key entry files

**No implementation code was generated.**
