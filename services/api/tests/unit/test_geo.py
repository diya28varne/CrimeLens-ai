"""Tests for bbox parsing helpers."""

import pytest

from app.infra.db.geo import parse_bbox, point_wkt


def test_point_wkt() -> None:
    assert point_wkt(77.5, 12.9) == "POINT(77.5 12.9)"


def test_parse_bbox_ok() -> None:
    assert parse_bbox("77.5,12.9,77.7,13.1") == (77.5, 12.9, 77.7, 13.1)


def test_parse_bbox_invalid() -> None:
    with pytest.raises(ValueError):
        parse_bbox("1,2,3")
    with pytest.raises(ValueError):
        parse_bbox("77.7,12.9,77.5,13.1")
