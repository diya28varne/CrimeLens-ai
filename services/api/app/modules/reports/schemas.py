"""Executive intelligence report schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ReportTemplateOut(BaseModel):
    id: str
    name: str
    description: str
    default_days: int


class TemplatesResponse(BaseModel):
    data: list[ReportTemplateOut]


class GenerateReportRequest(BaseModel):
    template_id: Literal["daily", "weekly", "festival"] = "weekly"
    from_: date | None = Field(default=None, alias="from")
    to: date | None = None
    district_id: UUID | None = None
    offense_codes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CoverOut(BaseModel):
    title: str
    subtitle: str
    prepared_for: str
    classification: str
    report_type: str
    date_label: str
    range_label: str
    generated_at: datetime


class OverviewOut(BaseModel):
    total_incidents: int
    delta_pct: float | None
    open_incidents: int
    high_severity: int
    by_severity: list[dict[str, Any]]
    by_offense: list[dict[str, Any]]
    trend_daily: list[dict[str, Any]]


class InsightOut(BaseModel):
    title: str
    body: str
    kind: Literal["observed", "forecast"] = "observed"


class HotspotOut(BaseModel):
    label: str
    risk_level: str
    score: float
    confidence: float
    factors: list[str]
    suggested_action: str


class PredictionOut(BaseModel):
    scope_name: str
    risk_score: float
    risk_band: str
    confidence: float
    kind: Literal["forecast"] = "forecast"
    note: str


class XaiSummaryOut(BaseModel):
    scope_name: str
    summary: str
    top_factors: list[str]
    confidence: float


class RecommendationOut(BaseModel):
    title: str
    rationale: str
    confidence: float
    priority: str


class ResourcePlanOut(BaseModel):
    division: str
    change: str
    note: str


class ChecklistItemOut(BaseModel):
    id: str
    text: str
    done: bool = False


class PresenterSlideOut(BaseModel):
    section_id: str
    title: str
    narration: str
    drill_href: str | None = None


class IntelligenceReportData(BaseModel):
    id: str
    template_id: str
    cover: CoverOut
    executive_summary: str
    overview: OverviewOut
    insights: list[InsightOut]
    hotspots: list[HotspotOut]
    predictions: list[PredictionOut]
    xai_summary: XaiSummaryOut | None
    recommendations: list[RecommendationOut]
    resource_plan: list[ResourcePlanOut]
    checklist: list[ChecklistItemOut]
    presenter_script: list[PresenterSlideOut]
    sources: list[dict[str, Any]]
    disclaimer: str
    generated_at: datetime


class GenerateReportResponse(BaseModel):
    data: IntelligenceReportData


class GetReportResponse(BaseModel):
    data: IntelligenceReportData
