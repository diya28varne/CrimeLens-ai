"""Crime Story Playback API schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StoryPoint(BaseModel):
    id: str
    lon: float
    lat: float
    offense_code: str
    offense_name: str
    severity: str
    occurred_at: datetime
    title: str | None = None


class DensityCell(BaseModel):
    lon: float
    lat: float
    count: int
    intensity: float  # 0–1
    stage: Literal[
        "individual",
        "small_cluster",
        "growing",
        "emerging_hotspot",
        "critical",
        "easing",
    ]


class StoryFrame(BaseModel):
    t: date
    cumulative_count: int
    new_count: int
    new_points: list[StoryPoint]
    density_cells: list[DensityCell]


class StoryChapter(BaseModel):
    id: str
    t_start: date
    t_end: date
    title: str
    narrative: str
    kind: Literal["observed"] = "observed"
    metrics: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class StoryEvent(BaseModel):
    id: str
    t: date
    label: str
    kind: str
    detail: str


class StoryRangeData(BaseModel):
    from_: date = Field(alias="from")
    to: date
    total_incidents: int
    offense_codes: list[str]
    bucket: str = "day"

    model_config = {"populate_by_name": True}


class StoryFramesData(BaseModel):
    range: StoryRangeData
    frames: list[StoryFrame]


class StoryFramesResponse(BaseModel):
    data: StoryFramesData


class StoryChaptersResponse(BaseModel):
    data: list[StoryChapter]


class StoryEventsResponse(BaseModel):
    data: list[StoryEvent]


class StoryRangeResponse(BaseModel):
    data: StoryRangeData


class DetectiveRequest(BaseModel):
    cursor_at: date
    window_days: int = Field(default=7, ge=1, le=30)
    offense_code: str | None = None
    district_id: UUID | None = None


class DetectiveFinding(BaseModel):
    question: str
    answer: str
    kind: Literal["observed", "forecast"] = "observed"
    evidence: list[str] = Field(default_factory=list)


class DetectiveBriefData(BaseModel):
    cursor_at: date
    window_from: date
    window_to: date
    headline: str
    findings: list[DetectiveFinding]
    suggested_actions: list[str]
    simulation_preset_id: str | None = None
    disclaimer: str
    confidence: float


class DetectiveResponse(BaseModel):
    data: DetectiveBriefData


class JourneyStep(BaseModel):
    key: str
    label: str
    at: datetime | None = None
    detail: str


class JourneyData(BaseModel):
    incident_id: UUID
    title: str
    offense_code: str
    steps: list[JourneyStep]
    nearby_similar: int
    disclaimer: str


class JourneyResponse(BaseModel):
    data: JourneyData
