"""Shared utilities — paths, config, logging, geo validation."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("crimelens_ml")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def ml_root() -> Path:
    """services/ml package root (configs/, datasets/, artifacts/)."""
    return Path(__file__).resolve().parents[3]


def load_yaml(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def load_common_config() -> dict[str, Any]:
    return load_yaml(ml_root() / "configs" / "common.yaml")


def ensure_dirs() -> dict[str, Path]:
    root = ml_root()
    paths = {
        "root": root,
        "datasets": root / "datasets",
        "raw": root / "datasets" / "raw",
        "processed": root / "datasets" / "processed",
        "engineered": root / "datasets" / "engineered",
        "synthetic": root / "datasets" / "synthetic",
        "artifacts": root / "artifacts",
        "reports": root / "reports",
        "configs": root / "configs",
        "schemas": root / "schemas",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def new_run_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def validate_karnataka_coords(lon: float, lat: float, bbox: dict[str, float]) -> bool:
    return (
        bbox["min_lon"] <= lon <= bbox["max_lon"]
        and bbox["min_lat"] <= lat <= bbox["max_lat"]
    )


# Approximate geohash base32 (precision truncated) — enough for cell ids without extra deps
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def geohash_encode(lat: float, lon: float, precision: int = 7) -> str:
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    geohash = []
    bits = [16, 8, 4, 2, 1]
    bit = 0
    ch = 0
    even = True
    while len(geohash) < precision:
        if even:
            mid = (lon_interval[0] + lon_interval[1]) / 2
            if lon > mid:
                ch |= bits[bit]
                lon_interval[0] = mid
            else:
                lon_interval[1] = mid
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2
            if lat > mid:
                ch |= bits[bit]
                lat_interval[0] = mid
            else:
                lat_interval[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)
