# Phase 1 — Foundation (implemented)

## Scope

Deliver a runnable platform skeleton without Identity/Crime/ML/AI business features.

## Delivered

| Area | Status |
|------|--------|
| Folder structure preserved | yes |
| Docker Compose db/redis/api/worker | yes |
| PostGIS + pgvector init | yes |
| `packages/py-domain` AuthContext + errors | yes |
| FastAPI composition root + request ID | yes |
| Health live/ready | yes |
| Worker heartbeat process | yes |
| Next.js shell + route placeholders | yes |
| CI lint/test/build jobs | yes |

## Explicitly deferred (await approval)

- Phase 2: Identity (auth, RBAC, sessions)
- Phase 3: Org + Incidents + PostGIS repositories
- Later: Spatial UI, Analytics, Predictions, Network, AI

## Approval gate

Approve Phase 1 before Identity module implementation begins.
