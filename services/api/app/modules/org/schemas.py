"""Organization list schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class DistrictOut(BaseModel):
    id: UUID
    code: str
    name: str
    state_code: str
    is_active: bool


class DistrictListResponse(BaseModel):
    data: list[DistrictOut]


class StationOut(BaseModel):
    id: UUID
    district_id: UUID
    code: str
    name: str
    is_active: bool


class StationListResponse(BaseModel):
    data: list[StationOut]
