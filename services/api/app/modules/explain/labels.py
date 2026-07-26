"""Officer-friendly labels for model feature keys."""

from __future__ import annotations

FEATURE_LABELS: dict[str, str] = {
    "lag_7d_count": "Previous similar crimes (7-day)",
    "weekend_flag": "Weekend activity",
    "severity_share_high": "Share of high-severity incidents",
    "hour_of_day": "Night / evening timing",
    "commercial_proximity": "Commercial zone proximity",
    "population_density": "Population density",
    "weather": "Weather conditions",
    "patrol_coverage": "Patrol coverage signal",
}


def friendly_label(feature: str) -> str:
    return FEATURE_LABELS.get(feature, feature.replace("_", " ").title())
