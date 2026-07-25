# CrimeLens AI

AI-Powered Crime Intelligence & Decision Support Platform for the Karnataka State Police Datathon.

## Phase status

- **Phase 1** Foundation — complete
- **Phase 2** Identity (auth/RBAC/sessions) — complete

Demo admin after `make migrate && make seed`:
`admin@crimelens.local` / `ChangeMe123!`

## Quick start

```bash
cp .env.example .env
make bootstrap
make up
make api-dev
# other terminal
make web-dev
```

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health/live

## Architecture docs

- `docs/architecture/FOLDER_STRUCTURE.md`
- `docs/database/SCHEMA.md`
- `docs/api/REST_API.md`
- `docs/ai/ARCHITECTURE.md`
