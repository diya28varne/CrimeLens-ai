"""Crime analytics trends/breakdown schemas."""

from __future__ import annotations

from pydantic import BaseModel


class TrendPoint(BaseModel):
    bucket_start: str
    count: int


class TrendSeries(BaseModel):
    key: str
    points: list[TrendPoint]


class TrendResponse(BaseModel):
    data: dict


class BreakdownItem(BaseModel):
    key: str
    name: str
    count: int


class BreakdownResponse(BaseModel):
    data: dict


class InsightsResponse(BaseModel):
    data: dict
