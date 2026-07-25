"""Prediction API schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PredictionRunSummary(BaseModel):
    id: UUID
    model_code: str
    model_version: str
    task: str
    metric: str
    scope_type: str
    horizon_start: datetime
    horizon_end: datetime
    generated_at: datetime
    is_current: bool
    status_banner: str = "fresh"


class PredictionValueOut(BaseModel):
    id: UUID
    scope: dict
    value: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    occurs_on: date | None = None
    properties: dict = Field(default_factory=dict)


class CurrentPredictionsData(BaseModel):
    run: PredictionRunSummary | None
    values: list[PredictionValueOut]


class CurrentPredictionsResponse(BaseModel):
    data: CurrentPredictionsData


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class FeatureContribution(BaseModel):
    feature: str
    value: float | str | None = None
    contribution: float


class ExplanationData(BaseModel):
    prediction_value_id: UUID
    model_version: str
    base_value: float
    output_value: float
    global_importance: list[FeatureImportance]
    local_contributions: list[FeatureContribution]
    summary_text: str | None = None


class ExplanationResponse(BaseModel):
    data: ExplanationData


class HotspotRunSummary(BaseModel):
    id: UUID
    method: str
    model_version: str | None
    window_start: datetime
    window_end: datetime
    is_current: bool


class HotspotFeatureOut(BaseModel):
    id: UUID
    rank: int
    score: float
    incident_count: int
    centroid: dict
    properties: dict = Field(default_factory=dict)


class HotspotsCurrentData(BaseModel):
    run: HotspotRunSummary | None
    features: list[HotspotFeatureOut]


class HotspotsCurrentResponse(BaseModel):
    data: HotspotsCurrentData


class ModelCard(BaseModel):
    model_code: str
    model_version: str
    task: str
    algorithm: str
    status: str
    metrics: dict
    train_window: dict | None = None


class ModelsResponse(BaseModel):
    data: list[ModelCard]


class RunsResponse(BaseModel):
    data: list[PredictionRunSummary]
