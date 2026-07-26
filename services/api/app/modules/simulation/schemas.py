"""Simulation API schemas."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ScenarioControls(BaseModel):
    patrol_delta_pct: int = Field(default=0, ge=-50, le=50)
    cctv_delta_pct: int = Field(default=0, ge=-50, le=50)
    public_event: bool = False
    event_zone: Literal[
        "central", "metro_corridor_a", "east", "west", "north", "south"
    ] = "central"
    time_of_day: Literal["morning", "afternoon", "evening", "night"] = "evening"
    day_type: Literal["weekday", "weekend", "holiday"] = "weekday"
    weather_stress: bool = False


class SimulationRunRequest(BaseModel):
    preset_id: str | None = None
    controls: ScenarioControls | None = None
    district_id: UUID | None = None


class ScenarioPresetOut(BaseModel):
    id: str
    name: str
    description: str
    controls: ScenarioControls


class ScenariosResponse(BaseModel):
    data: list[ScenarioPresetOut]


class MetricPair(BaseModel):
    key: str
    label: str
    baseline: float
    simulated: float
    unit: str = ""
    higher_is_better: bool | None = None


class SectorDelta(BaseModel):
    sector: str
    pct_change: float
    direction: Literal["up", "down", "flat"]
    note: str


class SimulationPoint(BaseModel):
    id: str
    kind: Literal["station", "hotspot"]
    label: str
    lon: float
    lat: float
    baseline_risk: float
    simulated_risk: float
    delta: float
    delta_pct: float


class BriefingOut(BaseModel):
    scenario_label: str
    current_risk_band: str
    predicted_changes: list[str]
    suggested_actions: list[str]
    confidence: float
    disclaimer: str


class MetricsSummary(BaseModel):
    aggregate_risk: float
    hotspot_count: int
    patrol_coverage: float
    resource_utilization: float
    ops_cost_index: float


class SimulationRunData(BaseModel):
    run_id: str
    scenario_label: str
    preset_id: str | None
    controls: ScenarioControls
    baseline: MetricsSummary
    simulated: MetricsSummary
    comparison: list[MetricPair]
    deltas: list[SectorDelta]
    points: list[SimulationPoint]
    event_zone: dict[str, Any]
    briefing: BriefingOut
    confidence: float
    disclaimer: str
    source: dict[str, Any] = Field(default_factory=dict)


class SimulationRunResponse(BaseModel):
    data: SimulationRunData
