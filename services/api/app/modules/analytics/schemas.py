"""Socio-economic analytics API schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class IndicatorRow(BaseModel):
    district_id: UUID
    district_code: str
    district_name: str
    year: int
    indicator_code: str
    value: float
    unit: str
    source: str | None = None


class IndicatorListResponse(BaseModel):
    data: list[IndicatorRow]


class CrimeMetricRow(BaseModel):
    district_id: UUID
    district_code: str
    district_name: str
    year: int
    incident_count: int
    crime_rate_per_100k: float
    high_severity_count: int


class CrimeMetricListResponse(BaseModel):
    data: list[CrimeMetricRow]


class ScatterPoint(BaseModel):
    district_id: UUID
    district_code: str
    district_name: str
    indicator_value: float
    crime_value: float


class CorrelationResult(BaseModel):
    year: int
    indicator_code: str
    crime_metric: Literal["crime_rate_per_100k", "incident_count"]
    method: str = "pearson"
    coefficient: float | None
    abs_coefficient: float | None
    sample_size: int
    interpretation: str
    points: list[ScatterPoint] = Field(default_factory=list)


class CorrelationResponse(BaseModel):
    data: CorrelationResult


class CorrelationSummary(BaseModel):
    year: int
    indicator_code: str
    crime_metric: str
    method: str
    coefficient: float | None
    abs_coefficient: float | None
    sample_size: int
    interpretation: str


class CorrelationListResponse(BaseModel):
    data: list[CorrelationSummary]
