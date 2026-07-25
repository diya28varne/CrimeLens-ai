"""Network API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NetworkNode(BaseModel):
    id: str
    label: str
    is_repeat_offender: bool
    incident_count: int = 0
    risk_flags: dict = Field(default_factory=dict)


class NetworkEdge(BaseModel):
    id: str
    source: str
    target: str
    link_type: str
    origin: str
    weight: float


class GraphMeta(BaseModel):
    truncated: bool = False
    node_count: int
    edge_count: int


class NetworkGraphData(BaseModel):
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    meta: GraphMeta


class NetworkGraphResponse(BaseModel):
    data: NetworkGraphData


class NamedCount(BaseModel):
    key: str
    name: str
    count: int


class RepeatOffenderRow(BaseModel):
    person_id: UUID
    full_name: str
    incident_count: int
    offense_mix: list[NamedCount] = Field(default_factory=list)
    last_occurred_at: datetime | None = None
    score: float


class RepeatOffendersResponse(BaseModel):
    data: list[RepeatOffenderRow]


class PersonDetail(BaseModel):
    id: UUID
    full_name: str
    alias: str | None = None
    is_repeat_offender: bool
    incident_count: int
    links_out_count: int
    risk_flags: dict = Field(default_factory=dict)


class PersonDetailResponse(BaseModel):
    data: PersonDetail
