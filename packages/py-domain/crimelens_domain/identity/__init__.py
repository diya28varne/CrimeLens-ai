"""Identity bounded context — AuthContext and permission primitives."""

from crimelens_domain.identity.auth_context import AuthContext, PermissionCode, RoleCode
from crimelens_domain.identity import permissions, roles
from crimelens_domain.identity.policies import (
    require_authenticated,
    require_district_access,
    require_permission,
    require_station_access,
)

__all__ = [
    "AuthContext",
    "PermissionCode",
    "RoleCode",
    "permissions",
    "roles",
    "require_authenticated",
    "require_district_access",
    "require_permission",
    "require_station_access",
]
