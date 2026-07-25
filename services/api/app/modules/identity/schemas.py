"""Pydantic schemas for Identity / Auth APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    status: Literal["active", "invited", "disabled"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    client: Literal["browser", "api"] = "browser"


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class LoginData(BaseModel):
    user: UserPublic
    access_token: str | None = None
    expires_at: datetime
    permissions: list[str]


class LoginResponse(BaseModel):
    data: LoginData


class Jurisdictions(BaseModel):
    district_ids: list[UUID]
    station_ids: list[UUID]


class MeData(BaseModel):
    user: UserPublic
    roles: list[str]
    permissions: list[str]
    jurisdictions: Jurisdictions


class MeResponse(BaseModel):
    data: MeData
