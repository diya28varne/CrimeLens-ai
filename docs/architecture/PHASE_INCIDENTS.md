# Incidents + PostGIS module

**Status:** Implemented  
**API version:** 0.4.0

## Delivered

- `offense_categories`, `offense_types`, `ingest_batches`, `incidents` (geography Point 4326 + GIST)
- Alembic `0003_incidents_postgis`
- `GET /org/districts`, `GET /org/stations`
- `GET /incidents`, `GET /incidents/{id}`, `POST /incidents/ingest`, ingest batch status
- `GET /offense-types`
- `GET /spatial/incidents` (GeoJSON bbox/radius)
- `GET /spatial/radius`
- Seed offenses + 8 Bengaluru sample incidents

## Run

```bash
make up && make migrate && make seed && make api-dev
```
