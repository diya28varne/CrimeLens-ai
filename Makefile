.PHONY: help bootstrap up down api-test domain-test web-dev api-dev migrate seed

help:
	@echo "CrimeLens AI commands"
	@echo "  make bootstrap   Install JS + Python deps"
	@echo "  make up          Start db/redis via Compose"
	@echo "  make down        Stop Compose stack"
	@echo "  make migrate     Run Alembic migrations"
	@echo "  make seed        Seed identity + socio + incidents + predictions + network"
	@echo "  make domain-test Run py-domain tests"
	@echo "  make api-test    Run API unit tests"
	@echo "  make api-dev     Run API locally"
	@echo "  make web-dev     Run Next.js locally"

bootstrap:
	pnpm install
	uv sync --all-packages

up:
	docker compose up --build -d db redis

down:
	docker compose down

migrate:
	cd services/api && alembic upgrade head

seed:
	uv run --package crimelens-api python -m app.modules.identity.seed
	uv run --package crimelens-api python -m app.modules.analytics.seed
	uv run --package crimelens-api python -m app.modules.incidents.seed
	uv run --package crimelens-api python -m app.modules.predictions.seed
	uv run --package crimelens-api python -m app.modules.network.seed

domain-test:
	uv run --package crimelens-domain pytest packages/py-domain/tests -q

api-test:
	uv run --package crimelens-api pytest services/api/tests/unit -q

api-dev:
	uv run --package crimelens-api uvicorn app.main:app --reload --app-dir services/api --host 0.0.0.0 --port 8000

web-dev:
	pnpm --filter @crimelens/web dev
