"""Scenario library presets for the Digital Twin simulator."""

from __future__ import annotations

from typing import Any

DISCLAIMER = (
    "Estimates from a decision model — not guarantees. "
    "Use for operational planning support only."
)

# Demo zone centroids (Bengaluru-oriented) for event / corridor stress
ZONES: dict[str, dict[str, Any]] = {
    "central": {
        "label": "Central Business District",
        "lon": 77.5946,
        "lat": 12.9716,
        "radius_km": 2.5,
    },
    "metro_corridor_a": {
        "label": "Metro Corridor A",
        "lon": 77.6050,
        "lat": 12.9800,
        "radius_km": 3.0,
    },
    "east": {
        "label": "East Bengaluru",
        "lon": 77.6400,
        "lat": 12.9780,
        "radius_km": 3.5,
    },
    "west": {
        "label": "West Bengaluru",
        "lon": 77.5500,
        "lat": 12.9700,
        "radius_km": 3.5,
    },
    "north": {
        "label": "North Bengaluru",
        "lon": 77.5900,
        "lat": 13.0350,
        "radius_km": 3.5,
    },
    "south": {
        "label": "South Bengaluru",
        "lon": 77.5950,
        "lat": 12.9100,
        "radius_km": 3.5,
    },
}

# Fallback station placement when GIS is absent
STATION_COORDS: dict[str, tuple[float, float]] = {
    "BLR-CENTRAL": (77.5946, 12.9716),
    "BLR-EAST": (77.6400, 12.9780),
    "BLR-WEST": (77.5500, 12.9700),
    "BLR-NORTH": (77.5900, 13.0350),
    "BLR-SOUTH": (77.5950, 12.9100),
    "BLR-MG": (77.6030, 12.9750),
    "BLR-CUBBON": (77.5800, 12.9650),
}

DEFAULT_CONTROLS: dict[str, Any] = {
    "patrol_delta_pct": 0,
    "cctv_delta_pct": 0,
    "public_event": False,
    "event_zone": "central",
    "time_of_day": "evening",
    "day_type": "weekday",
    "weather_stress": False,
}

SCENARIO_PRESETS: list[dict[str, Any]] = [
    {
        "id": "weekend_festival",
        "name": "Weekend Festival",
        "description": "Large public gathering near CBD with light patrol uplift.",
        "controls": {
            **DEFAULT_CONTROLS,
            "public_event": True,
            "event_zone": "central",
            "day_type": "weekend",
            "time_of_day": "evening",
            "patrol_delta_pct": 15,
            "cctv_delta_pct": 10,
        },
    },
    {
        "id": "heavy_rain",
        "name": "Heavy Rain",
        "description": "Weather stress during evening hours across the city.",
        "controls": {
            **DEFAULT_CONTROLS,
            "weather_stress": True,
            "time_of_day": "evening",
            "day_type": "weekday",
        },
    },
    {
        "id": "vip_movement",
        "name": "VIP Movement",
        "description": "Elevated coverage along Metro Corridor A for a protected movement.",
        "controls": {
            **DEFAULT_CONTROLS,
            "public_event": True,
            "event_zone": "metro_corridor_a",
            "patrol_delta_pct": 25,
            "cctv_delta_pct": 20,
            "time_of_day": "afternoon",
            "day_type": "weekday",
        },
    },
    {
        "id": "major_sporting_event",
        "name": "Major Sporting Event",
        "description": "Stadium-scale weekend event with spillover risk.",
        "controls": {
            **DEFAULT_CONTROLS,
            "public_event": True,
            "event_zone": "east",
            "day_type": "weekend",
            "time_of_day": "evening",
            "patrol_delta_pct": 20,
            "cctv_delta_pct": 15,
        },
    },
    {
        "id": "school_holiday",
        "name": "School Holiday",
        "description": "Holiday day-type shift with residential watch emphasis.",
        "controls": {
            **DEFAULT_CONTROLS,
            "day_type": "holiday",
            "time_of_day": "afternoon",
            "event_zone": "south",
            "patrol_delta_pct": 5,
        },
    },
    {
        "id": "metro_service_disruption",
        "name": "Metro Service Disruption",
        "description": "Corridor stress and alternate-route spillover near Metro A.",
        "controls": {
            **DEFAULT_CONTROLS,
            "public_event": True,
            "event_zone": "metro_corridor_a",
            "time_of_day": "morning",
            "day_type": "weekday",
            "patrol_delta_pct": 10,
            "cctv_delta_pct": 5,
        },
    },
]


def get_preset(preset_id: str | None) -> dict[str, Any] | None:
    if not preset_id:
        return None
    for p in SCENARIO_PRESETS:
        if p["id"] == preset_id:
            return p
    return None


def merge_controls(preset_id: str | None, overrides: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """Return (scenario_label, merged_controls)."""
    preset = get_preset(preset_id)
    controls = dict(DEFAULT_CONTROLS)
    label = "Custom scenario"
    if preset:
        controls.update(preset["controls"])
        label = preset["name"]
    if overrides:
        controls.update({k: v for k, v in overrides.items() if v is not None})
        if not preset or overrides:
            # Keep library name if only loading preset; mark custom if overridden without preset
            if preset and overrides and any(
                overrides.get(k) != preset["controls"].get(k) for k in overrides
            ):
                label = f"{preset['name']} (modified)"
            elif not preset:
                label = "Custom scenario"
    return label, controls
