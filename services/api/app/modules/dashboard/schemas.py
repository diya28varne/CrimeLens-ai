"""Dashboard response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardScope(BaseModel):
    district_id: UUID | None = None
    station_id: UUID | None = None
    from_: datetime = Field(alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class KpiSet(BaseModel):
    total_incidents: int
    total_incidents_delta_pct: float | None
    open_incidents: int
    high_severity: int
    hotspot_count: int = 0
    avg_risk_score: float | None = None


class NamedCount(BaseModel):
    key: str
    name: str
    count: int


class DailyCount(BaseModel):
    date: str
    count: int


class ModelPointer(BaseModel):
    prediction_run_id: str | None = None
    model_version: str | None = None
    generated_at: datetime | None = None
    is_stale: bool = True


class DashboardOverview(BaseModel):
    scope: DashboardScope
    kpis: KpiSet
    by_severity: list[NamedCount]
    by_offense_top: list[NamedCount]
    trend_daily: list[DailyCount]
    model: ModelPointer


class DashboardOverviewResponse(BaseModel):
    data: DashboardOverview


class DashboardAlert(BaseModel):
    id: str
    severity: str
    title: str
    body: str
    district_id: UUID | None = None
    station_id: UUID | None = None
    metric: str
    value: float
    baseline: float | None = None
    href: str | None = None


class DashboardAlertsResponse(BaseModel):
    data: list[DashboardAlert]
