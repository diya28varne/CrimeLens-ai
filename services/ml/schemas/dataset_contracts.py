"""Dataset schema contracts (JSON Schema — Pandera optional later)."""

RISK_INTELLIGENCE_SCHEMA = {
    "$id": "crimelens.risk_intelligence.v1",
    "title": "Crime Risk Intelligence Dataset",
    "owner_module": "predictions",
    "target": "risk_level",
    "required": [
        "district_code",
        "station_code",
        "grid_cell_id",
        "as_of_ts",
        "geohash",
        "CrimeFrequency7Days",
        "CrimeFrequency30Days",
        "risk_level",
        "risk_score",
        "feature_set_id",
    ],
}

HOTSPOT_EVOLUTION_SCHEMA = {
    "$id": "crimelens.hotspot_evolution.v1",
    "title": "Smart Hotspot Evolution Dataset",
    "owner_module": "predictions+simulation",
    "target": "hotspot_growth",
    "required": [
        "grid_cell_id",
        "centroid_lat",
        "centroid_lon",
        "incident_density",
        "density_delta_7d",
        "hotspot_growth",
    ],
}
