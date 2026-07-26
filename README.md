# CrimeLens AI

**AI-powered crime intelligence and decision-support platform** for the Karnataka State Police Datathon.

CrimeLens turns incident, geospatial, network, and socio-economic data into operational awareness and strategic guidance — with explainable models, simulation, and executive briefings built for police workflows.

---

## Table of contents

- [Overview](#overview)
- [Key capabilities](#key-capabilities)
- [Application surfaces](#application-surfaces)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Quick start](#quick-start)
- [Windows notes](#windows-notes)
- [Demo access](#demo-access)
- [Common commands](#common-commands)
- [Configuration](#configuration)
- [API & health](#api--health)
- [Documentation](#documentation)
- [Security & responsible use](#security--responsible-use)
- [Project status](#project-status)

---

## Overview

CrimeLens AI is a modular monorepo that delivers:

| Layer | Role |
|-------|------|
| **Web console** | Command overview, deep analytics, map intelligence, prediction, network analysis, and five flagship AI workflows |
| **REST API** | Authenticated FastAPI service with RBAC, jurisdiction scoping, incident/analytics/prediction/network modules |
| **Data platform** | PostgreSQL + PostGIS for spatial crime data; Redis for sessions/cache |
| **Domain library** | Shared Python domain models, permissions, and identity contracts |

**Design posture:** decision support with auditability — not black-box automation. Predictive and AI outputs are intended to assist officers and commanders; human review remains in the loop.

---

## Key capabilities

### Operational intelligence

- **Dashboard** — Live KPIs, severity mix, and alerts for at-a-glance command awareness
- **Analytics** — Period-over-period impact, spike detection, hour/day patterns, offense concentration, and socio-economic Pearson correlations
- **Geospatial map** — Interactive MapLibre + deck.gl visualization with district drill-down
- **Prediction** — Risk scoring surfaces for forward-looking deployment planning
- **Network analysis** — Link analysis and repeat-offender oriented exploration

### Flagship AI workflows (P1)

| Feature | Route | Purpose |
|---------|-------|---------|
| Digital Twin Simulator | `/simulation` | Scenario simulation for “what if” resource and pattern exploration |
| Strategic Intelligence Advisor | `/advisor` | Actionable deployment and priority guidance |
| Crime Story Playback | `/story` | Temporal narrative / detective-mode reconstruction |
| Explainable AI (XAI) | `/explain` | Model decision breakdowns for trust and review |
| Executive Intelligence Reports | `/reports` | Briefing builder with present/print-oriented output |

### Platform foundations

- JWT + cookie session auth with role-based access control (RBAC)
- Jurisdiction-aware data scoping (district / station)
- Admin overview (users, roles, permissions, feature flags, AI audit snapshot)
- User settings (profile and local preferences)
- OpenAPI-documented REST surface under `/api/v1`

---

## Application surfaces

| Route | Description |
|-------|-------------|
| `/dashboard` | Ops overview — KPIs and alerts |
| `/analytics` | Deep analysis — impact, patterns, socio drivers |
| `/map` | Geospatial intelligence |
| `/prediction` | Predictive risk views |
| `/simulation` | Digital twin simulator |
| `/advisor` | Strategic intelligence advisor |
| `/story` | Crime story playback |
| `/explain` | Explainable AI engine |
| `/network` | Network / link analysis |
| `/reports` | Executive reports + present mode |
| `/ai` | AI copilot entry |
| `/settings` | User preferences |
| `/admin` | Administration & audit snapshot |
| `/login` | Sign-in |

**Dashboard vs Analytics:** Dashboard answers “what is happening now?” Analytics answers “why, how has it changed, and where should we act?”

---

## Architecture

```text
┌─────────────────┐     HTTPS/JSON      ┌──────────────────────┐
│  Next.js Web    │ ◄─────────────────► │  FastAPI (/api/v1)   │
│  (apps/web)     │                     │  (services/api)      │
└─────────────────┘                     └──────────┬───────────┘
                                                   │
                          ┌────────────────────────┼────────────────────────┐
                          ▼                        ▼                        ▼
                   PostgreSQL+PostGIS            Redis                 Domain package
                   (incidents, GIS,              (sessions /           (packages/
                    identity, analytics)          cache)                py-domain)
```

- **Modular monolith** first (see ADR-0001); extract services only when scale requires it
- Spatial standards via **PostGIS**; vector/AI options documented in ADRs (pgvector, PydanticAI agents)
- Map stack: **MapLibre GL** + **deck.gl**
- Charts: **Apache ECharts**

---

## Technology stack

| Area | Choice |
|------|--------|
| Frontend | Next.js 15, React 19, TypeScript, Turbopack (local), Tailwind CSS 4 |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic Settings |
| Workspace | pnpm + Turborepo (JS), uv (Python) |
| Database | PostgreSQL 16 + PostGIS |
| Cache / sessions | Redis 7 |
| Containers | Docker Compose (`db`, `redis`, `api`, optional `worker`) |
| Auth | JWT access/refresh, httpOnly cookies, RBAC permissions |

---

## Repository layout

```text
CrimeLens-ai/
├── apps/web/              # Next.js command console
├── services/api/          # FastAPI application + Alembic migrations
├── services/worker/       # Background worker runtime
├── services/ml/           # ML pipelines workspace
├── packages/py-domain/    # Shared domain / identity / permissions
├── packages/web-ui/       # Shared UI package (workspace)
├── docs/                  # Architecture, API, product, ADRs, runbooks
├── infra/                 # Dockerfiles, initdb, observability configs
├── scripts/               # Bootstrap and operational helpers
├── docker-compose.yml     # Local stack
├── Makefile               # Common developer entrypoints
└── .env.example           # Environment template
```

---

## Prerequisites

- **Node.js** (see `.nvmrc`) and **pnpm** 9+
- **Python** 3.12+ and **uv**
- **Docker Desktop** (or compatible Docker Engine + Compose)
- Git

Optional: GNU Make (or run equivalent commands listed below on Windows PowerShell).

---

## Environment Setup

CrimeLens loads configuration from a local `.env` file. That file is **gitignored** and must never be pushed to GitHub.

### 1. Copy the template

```bash
cp .env.example .env
```

**Windows (Command Prompt):**

```bat
copy .env.example .env
```

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

You may also create `.env` manually and paste values from `.env.example`.

### 2. Fill in your own values

Open `.env` and set at least:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Local database credentials |
| `POSTGRES_URL` or `DATABASE_URL` | SQLAlchemy / app connection string |
| `REDIS_URL` | Redis connection |
| `JWT_SECRET` | Signing key for access/refresh tokens (use a long random value) |
| `GEMINI_API_KEY` | Optional — only if AI features are enabled |
| `QDRANT_API_KEY` / `QDRANT_URL` | Optional — vector store |
| `NEXT_PUBLIC_API_BASE_URL` | Browser → API base URL |

`.env.example` contains **placeholders only** (no real API keys). It is safe to commit. Your filled `.env` is not.

### 3. Never commit secrets

- Do **not** `git add .env`
- Do **not** commit `.env.local`, `.env.development`, or `.env.production`
- If a secret was ever committed, rotate it immediately and remove it from Git history (see [Security & responsible use](#security--responsible-use))

---

## Quick start

### 1. Configure environment

Follow [Environment Setup](#environment-setup) (`cp .env.example .env`, then fill values).

### 2. Install dependencies

```bash
make bootstrap
# equivalent:
#   pnpm install
#   uv sync --all-packages
```

### 3. Start infrastructure and API

**Recommended (all platforms):** run database, Redis, and API in Docker:

```bash
docker compose up -d --build db redis api
```

Then apply migrations and seed demo data (from the host, with Compose DB exposed on `localhost:5432`):

```bash
make migrate
make seed
```

### 4. Start the web app

```bash
make web-dev
# or: pnpm --filter @crimelens/web dev
```

### 5. Open the console

| Service | URL |
|---------|-----|
| Web application | http://localhost:3000 |
| Interactive API docs (Swagger) | http://localhost:8000/docs |
| OpenAPI schema | http://localhost:8000/openapi.json |
| Liveness | http://localhost:8000/api/v1/health/live |

---

## Windows notes

On Windows, prefer running the **API inside Docker** (`docker compose up -d api`) rather than host `uvicorn`. Host-side async PostgreSQL clients can hit event-loop limitations on Windows.

The web app uses **Turbopack** (`next dev --turbopack`). If the router fails to mount after path-casing changes, clear `apps/web/.next` and restart `make web-dev`.

PowerShell does not support `&&` in older versions; use `;` or separate commands:

```powershell
docker compose build api; docker compose up -d --no-deps api
```

---

## Demo access

After `make migrate` and `make seed`:

| Field | Value |
|-------|-------|
| Email | `admin@crimelens.local` |
| Password | `ChangeMe123!` |

Change these credentials before any shared or production-like deployment.

---

## Common commands

| Command | Description |
|---------|-------------|
| `make bootstrap` | Install JS (pnpm) and Python (uv) dependencies |
| `make up` | Start `db` + `redis` only |
| `make down` | Stop the Compose stack |
| `make migrate` | Run Alembic migrations |
| `make seed` | Seed identity, socio-economic, incidents, predictions, network |
| `make api-dev` | Run API on the host (prefer Docker on Windows) |
| `make web-dev` | Run Next.js on port 3000 |
| `make domain-test` | Run `py-domain` unit tests |
| `make api-test` | Run API unit tests |

Docker rebuild after backend changes:

```bash
docker compose build api
docker compose up -d --no-deps api
```

---

## Configuration

Primary template: [`.env.example`](./.env.example).

| Category | Variables (examples) |
|----------|----------------------|
| Application | `APP_ENV`, `API_PORT`, `CORS_ORIGINS`, `LOG_LEVEL` |
| Feature flags | `AI_ENABLED`, `ML_ENABLED`, `NETWORK_ENABLED` |
| Database | `POSTGRES_*`, `POSTGRES_URL` |
| Redis | `REDIS_URL` |
| Auth | `JWT_SECRET`, `JWT_ACCESS_TTL_MINUTES`, `JWT_REFRESH_TTL_DAYS` |
| AI / observability | `GEMINI_API_KEY`, `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT` |
| Web | `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_MAP_STYLE_URL` |

The Compose `api` service overrides `POSTGRES_URL` / `REDIS_URL` to use Docker network hostnames (`db`, `redis`).

---

## API & health

- **Base path:** `/api/v1`
- **Auth:** Bearer token and/or httpOnly session cookies
- **Errors:** Structured `{ error: { code, message, details, request_id } }`

Representative module groups:

- Identity / auth
- Incidents (PostGIS-backed)
- Analytics (trends, breakdown, **insights**, socio-economic correlation)
- Predictions
- Network
- Simulation, advisor, story, explain, reports
- Admin overview

Contract exploration: http://localhost:8000/docs  
Design reference: [`docs/api/REST_API.md`](./docs/api/REST_API.md)

---

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/architecture/FOLDER_STRUCTURE.md`](./docs/architecture/FOLDER_STRUCTURE.md) | Monorepo structure and rationale |
| [`docs/architecture/PHASE_MAP.md`](./docs/architecture/PHASE_MAP.md) | Phase roadmap |
| [`docs/database/SCHEMA.md`](./docs/database/SCHEMA.md) | Data model |
| [`docs/api/REST_API.md`](./docs/api/REST_API.md) | REST design |
| [`docs/ai/ARCHITECTURE.md`](./docs/ai/ARCHITECTURE.md) | AI system design |
| [`docs/product/mvp-scope.md`](./docs/product/mvp-scope.md) | Datathon MVP cuts |
| [`docs/product/features/`](./docs/product/features/) | Flagship feature briefs (1–5) |
| [`docs/adr/`](./docs/adr/) | Architecture decision records |
| [`docs/security/threat-model.md`](./docs/security/threat-model.md) | Threat model |
| [`docs/runbooks/`](./docs/runbooks/) | Operational runbooks |

---

## Security & responsible use

- Demo credentials and default JWT secrets are **local-only**. Rotate before any shared environment.
- Do not commit `.env`, real credentials, or production datasets. See [`SECURITY.md`](./SECURITY.md).
- Predictions and advisor output are **decision-support aids**; they must not be treated as sole grounds for enforcement action.
- Jurisdiction scoping and RBAC are enforced server-side — never rely on the UI alone for authorization.

### If a `.env` file was ever committed

`.env` is currently **not** tracked in this repository. If it becomes tracked in the future (or on a fork), remove it from the index **without deleting your local file**:

```bash
git rm --cached .env
git commit -m "chore: stop tracking .env"
```

Then rotate every secret that lived in that file. If the secret was pushed to a remote, also purge it from history (e.g. `git filter-repo` or BFG) and force-push only with team agreement — rotating credentials is mandatory either way.

---

## Project status

| Area | Status |
|------|--------|
| Foundation (Compose, monorepo, health) | Complete |
| Identity (auth, RBAC, sessions) | Complete |
| Incidents + PostGIS map | Live |
| Dashboard & Analytics (incl. insights) | Live |
| Socio-economic correlation | Live |
| Prediction & network modules | Live |
| Flagship features 1–5 | Live (P1) |
| Settings & Admin panels | Live |

Current API version is published in OpenAPI (`info.version`) when the stack is running.

---

## License

See [`LICENSE`](./LICENSE) for project licensing terms applicable to the datathon / agency context.
