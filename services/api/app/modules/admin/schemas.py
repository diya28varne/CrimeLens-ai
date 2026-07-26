"""Admin console schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AdminUserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    status: str
    roles: list[str]


class AdminRoleOut(BaseModel):
    code: str
    name: str
    permission_count: int


class AdminOverviewData(BaseModel):
    api_version: str
    users: list[AdminUserOut]
    roles: list[AdminRoleOut]
    permission_codes: list[str]
    feature_flags: list[dict]


class AdminOverviewResponse(BaseModel):
    data: AdminOverviewData
