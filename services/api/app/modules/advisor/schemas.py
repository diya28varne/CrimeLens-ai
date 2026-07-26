"""Advisor API schemas — Strategic Intelligence briefing."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    kind: str
    label: str
    detail: str
    value: float | int | str | None = None
    href: str | None = None


class PatternOut(BaseModel):
    id: str
    title: str
    explanation: str
    kind: Literal["observed", "forecast"] = "observed"
    confidence: float
    strength: Literal["high", "medium", "low"] = "medium"
    evidence: list[EvidenceItem] = Field(default_factory=list)


class RiskAreaOut(BaseModel):
    id: str
    name: str
    risk_band: Literal["High", "Medium", "Elevated-low", "Low"]
    risk_score: float
    confidence: float
    why: str
    kind: Literal["observed", "forecast"] = "forecast"
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ActionOut(BaseModel):
    id: str
    title: str
    rationale: str
    confidence: float
    priority: Literal["high", "medium", "low"] = "medium"
    simulation_preset_id: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)


class TimelineEntryOut(BaseModel):
    id: str
    generated_at: datetime
    summary_excerpt: str
    recommendation_count: int
    hotspot_realized_note: str | None = None
    accuracy_note: str | None = None
    acted_on_demo: bool | None = None


class SummaryBlock(BaseModel):
    headline: str
    body: str
    week_over_week_pct: float | None = None
    kind_tags: list[Literal["observed", "forecast"]] = Field(default_factory=list)


class AdvisorBriefData(BaseModel):
    id: str
    generated_at: datetime
    summary: SummaryBlock
    patterns: list[PatternOut]
    risk_areas: list[RiskAreaOut]
    actions: list[ActionOut]
    timeline: list[TimelineEntryOut] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    disclaimer: str
    confidence: float


class AdvisorBriefResponse(BaseModel):
    data: AdvisorBriefData


class AdvisorHistoryResponse(BaseModel):
    data: list[TimelineEntryOut]
