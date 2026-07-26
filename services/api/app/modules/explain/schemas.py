"""Explainable AI Decision Engine schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FactorOut(BaseModel):
    feature: str
    label: str
    contribution: float
    share_pct: float
    raw_value: float | str | None = None


class EvidenceOut(BaseModel):
    id: str
    label: str
    detail: str
    checked: bool = True
    href: str | None = None


class ScenarioOut(BaseModel):
    id: str
    label: str
    risk_score: float
    risk_band: str
    delta_pct: float
    why: str


class SimilarCaseOut(BaseModel):
    title: str
    detail: str
    period: str
    analogy_note: str


class TimelinePointOut(BaseModel):
    day_label: str
    dominant_factor: str
    note: str


class RecommendationOut(BaseModel):
    title: str
    reasons: list[str]
    expected_risk_reduction_pct: float
    confidence: float


class DecisionCardData(BaseModel):
    audit_id: str
    prediction_value_id: UUID
    scope_name: str
    risk_score: float
    risk_band: Literal["High", "Medium", "Elevated-low", "Low"]
    confidence: float
    confidence_band: Literal["High", "Moderate", "Low"]
    summary: str
    factors: list[FactorOut]
    evidence: list[EvidenceOut]
    scenarios: list[ScenarioOut]
    similar_cases: list[SimilarCaseOut]
    timeline: list[TimelinePointOut]
    recommendation: RecommendationOut | None = None
    model_version: str
    base_value: float
    generated_at: datetime
    disclaimer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class DecisionCardResponse(BaseModel):
    data: DecisionCardData


class WhatIfRequest(BaseModel):
    scenario_id: str | None = None
    patrol_delta_pct: int | None = Field(default=None, ge=-50, le=50)
    cctv_delta_pct: int | None = Field(default=None, ge=-50, le=50)
    public_event: bool | None = None


class WhatIfData(BaseModel):
    prediction_value_id: UUID
    baseline_score: float
    scenarios: list[ScenarioOut]
    disclaimer: str


class WhatIfResponse(BaseModel):
    data: WhatIfData


class AuditRecordOut(BaseModel):
    id: str
    created_at: datetime
    prediction_value_id: UUID
    scope_name: str
    risk_score: float
    risk_band: str
    confidence: float
    summary: str
    top_factors: list[str]
    recommendation: str | None = None
    outcome_status: Literal["pending", "demo_matched", "demo_missed"] = "pending"
    outcome_note: str | None = None


class AuditListResponse(BaseModel):
    data: list[AuditRecordOut]


class AuditDetailResponse(BaseModel):
    data: AuditRecordOut
    card: DecisionCardData | None = None
