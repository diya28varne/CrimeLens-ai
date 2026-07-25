"""Geospatial helpers for PostGIS geography points."""

from __future__ import annotations

from geoalchemy2.elements import WKTElement


def point_wkt(lon: float, lat: float) -> str:
    return f"POINT({lon} {lat})"


def point_geography(lon: float, lat: float) -> WKTElement:
    return WKTElement(point_wkt(lon, lat), srid=4326)


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    """Parse 'minLon,minLat,maxLon,maxLat'."""
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be minLon,minLat,maxLon,maxLat")
    min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("bbox bounds are invalid")
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("longitude out of range")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("latitude out of range")
    return min_lon, min_lat, max_lon, max_lat
