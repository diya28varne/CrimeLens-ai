# Socio-Economic Crime Correlation

**Status:** Implemented (module)  
**Permission:** `analytics:read`  
**Datathon coverage:** closes “Socio-economic crime correlation”

## Tables
- `socio_economic_indicators`
- `district_crime_metrics`
- `socio_crime_correlations` (schema ready; live compute also available)

## APIs
- `GET /api/v1/analytics/socio-economic/indicators`
- `GET /api/v1/analytics/socio-economic/crime-metrics`
- `GET /api/v1/analytics/socio-economic/correlation`
- `GET /api/v1/analytics/socio-economic/correlations`

## Seed
```bash
# after migrate
uv run --package crimelens-api python -m app.modules.identity.seed
uv run --package crimelens-api python -m app.modules.analytics.seed
```

Demo year: **2024**, 8 Karnataka districts, indicators include unemployment, literacy, density, poverty, urban %.
