"""Identity policy unit tests."""

from uuid import uuid4

import pytest

from crimelens_domain.identity import AuthContext, require_permission
from crimelens_domain.identity.permissions import ADMIN_USERS, INCIDENT_READ
from crimelens_domain.shared.errors import ForbiddenError


def test_require_permission_allows() -> None:
    ctx = AuthContext(user_id=uuid4(), permissions=(INCIDENT_READ,))
    require_permission(ctx, INCIDENT_READ)


def test_require_permission_denies() -> None:
    ctx = AuthContext(user_id=uuid4(), permissions=(INCIDENT_READ,))
    with pytest.raises(ForbiddenError):
        require_permission(ctx, ADMIN_USERS)
