"""Canonical socio-economic indicator codes for Karnataka district analytics."""

from __future__ import annotations

from typing import Final

INDICATOR_CATALOG: Final[dict[str, dict[str, str]]] = {
    "unemployment_rate": {"unit": "%", "label": "Unemployment rate"},
    "literacy_rate": {"unit": "%", "label": "Literacy rate"},
    "population_density": {"unit": "per_km2", "label": "Population density"},
    "poverty_index": {"unit": "index", "label": "Poverty index"},
    "urban_pct": {"unit": "%", "label": "Urban population share"},
}
