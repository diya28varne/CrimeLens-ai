"""PostGIS extract stubs — production path replaces synthetic when DATABASE_URL/POSTGRES_URL is set."""

from __future__ import annotations

import os
from typing import Any


EXTRACT_SQL = {
    "risk_cell_features": """
        -- Phase C+ extractor sketch (not auto-run without explicit --from-db)
        -- Aggregate incidents to geohash cells with point-in-time bounds.
        SELECT
          d.code AS district_code,
          s.code AS station_code,
          -- ST_GeoHash(i.location::geometry, 7) AS geohash,
          date_trunc('day', i.occurred_at) AS as_of_ts,
          count(*) FILTER (WHERE i.occurred_at >= now() - interval '7 days') AS incidents_7d,
          count(*) FILTER (WHERE i.occurred_at >= now() - interval '30 days') AS incidents_30d
        FROM incidents i
        JOIN districts d ON d.id = i.district_id
        JOIN police_stations s ON s.id = i.station_id
        WHERE i.deleted_at IS NULL
        GROUP BY 1, 2, 3
        LIMIT 0;  -- sketch only
    """,
}


def db_url_from_env() -> str | None:
    return os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")


def extract_status() -> dict[str, Any]:
    url = db_url_from_env()
    return {
        "database_configured": bool(url),
        "mode": "postgres" if url else "synthetic_fallback",
        "note": (
            "Phase C keeps synthetic/domain generator as default for offline CI. "
            "Wire SQL extracts in worker jobs when promoting to staging."
        ),
        "queries_defined": list(EXTRACT_SQL.keys()),
    }
