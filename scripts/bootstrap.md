Bootstrap CrimeLens locally (Phase 1):

1. Install Node 22+, pnpm 9, Python 3.12, uv, Docker.
2. `cp .env.example .env`
3. `pnpm install`
4. `uv sync --all-packages`
5. `docker compose up --build -d db redis`
6. `make api-dev` and `make web-dev`
