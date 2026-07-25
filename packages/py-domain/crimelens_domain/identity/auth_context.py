"""Authentication context passed through API, tools, and repositories."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


RoleCode = str
PermissionCode = str


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Immutable security principal for a single request or job."""

    user_id: UUID
    roles: tuple[RoleCode, ...] = ()
    permissions: tuple[PermissionCode, ...] = ()
    allowed_district_ids: tuple[UUID, ...] = ()
    allowed_station_ids: tuple[UUID, ...] = ()
    request_id: str | None = None
    is_superuser: bool = False

    def has_permission(self, code: PermissionCode) -> bool:
        if self.is_superuser:
            return True
        return code in self.permissions

    def can_access_district(self, district_id: UUID) -> bool:
        if self.is_superuser:
            return True
        if not self.allowed_district_ids and not self.allowed_station_ids:
            return False
        return district_id in self.allowed_district_ids

    def can_access_station(self, station_id: UUID) -> bool:
        if self.is_superuser:
            return True
        return station_id in self.allowed_station_ids
