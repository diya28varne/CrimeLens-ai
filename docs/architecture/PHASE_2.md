# Phase 2 — Identity (implemented)

## Scope

Authentication, RBAC, sessions, jurisdiction claims, `/api/v1/auth/*`.

## Delivered

| Item | Status |
|------|--------|
| Permission + role catalogs in `py-domain` | yes |
| Auth policies (`require_permission`, jurisdiction) | yes |
| ORM models: users/roles/permissions/sessions/jurisdictions + minimal districts/stations | yes |
| Alembic migration `0001_identity` | yes |
| Argon2 passwords + JWT access + hashed refresh sessions | yes |
| Endpoints: login, refresh, logout, me | yes |
| Cookie (`cl_access`/`cl_refresh`) + Bearer support | yes |
| Seed script for admin + BLR demo jurisdiction | yes |
| Unit tests (security + policies) | yes |

## Demo credentials (after seed)

- Email: `admin@crimelens.local`
- Password: `ChangeMe123!`

## Commands

```bash
docker compose up -d db redis
cd services/api && alembic upgrade head
python -m app.modules.identity.seed   # from services/api with PYTHONPATH=.
```

Or from repo root via Make targets once configured.

## Deferred

Org full GIS boundaries, incidents, map, analytics, predictions, AI.
