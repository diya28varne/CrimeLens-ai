"""Incident API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    lon: float
    lat: float


class OffenseTypeRef(BaseModel):
    id: UUID
    code: str
    name: str


class IncidentSummary(BaseModel):
    id: UUID
    external_ref: str | None
    offense_type: OffenseTypeRef
    district_id: UUID
    station_id: UUID
    status: str
    severity: str
    occurred_at: datetime
    location: GeoPoint
    title: str | None


class PageMeta(BaseModel):
    next_cursor: str | None
    limit: int


class IncidentListResponse(BaseModel):
    data: list[IncidentSummary]
    page: PageMeta


class IncidentDetail(IncidentSummary):
    description: str | None
    reported_at: datetime | None
    registered_at: datetime | None
    address_text: str | None
    source: str
    properties: dict


class IncidentDetailResponse(BaseModel):
    data: IncidentDetail


class OffenseTypeOut(BaseModel):
    id: UUID
    code: str
    name: str
    category: str
    default_severity: str


class OffenseTypeListResponse(BaseModel):
    data: list[OffenseTypeOut]


class IncidentIngestRow(BaseModel):
    external_ref: str | None = None
    offense_code: str
    station_code: str
    occurred_at: datetime
    lon: float
    lat: float
    status: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None
    properties: dict = Field(default_factory=dict)


class IncidentIngestRequest(BaseModel):
    format: Literal["json"] = "json"
    rows: list[IncidentIngestRow]
    dry_run: bool = False


class IngestError(BaseModel):
    row: int
    code: str
    message: str


class IncidentIngestData(BaseModel):
    batch_id: UUID | None
    accepted: int
    rejected: int
    errors: list[IngestError]
    job_id: UUID | None = None


class IncidentIngestResponse(BaseModel):
    data: IncidentIngestData


class IngestBatchStatus(BaseModel):
    id: UUID
    source: str
    row_count: int | None
    success_count: int | None
    error_count: int | None
    started_at: datetime
    finished_at: datetime | None
    errors: list


class IngestBatchResponse(BaseModel):
    data: IngestBatchStatus
