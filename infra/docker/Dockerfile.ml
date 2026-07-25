# ML job image — Phase 1 placeholder runtime; pipelines land in later phases.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv
COPY pyproject.toml ./
COPY packages/py-domain ./packages/py-domain
COPY services/ml ./services/ml

WORKDIR /app/services/ml
RUN uv sync --no-dev || true

CMD ["python", "-c", "print('crimelens-ml image ready')"]
