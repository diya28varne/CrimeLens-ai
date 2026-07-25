"""Domain unit tests."""

from uuid import uuid4

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared import ForbiddenError, NotFoundError


def test_auth_context_permission() -> None:
    ctx = AuthContext(
        user_id=uuid4(),
        permissions=("incident:read",),
    )
    assert ctx.has_permission("incident:read")
    assert not ctx.has_permission("admin:users")


def test_auth_context_superuser() -> None:
    ctx = AuthContext(user_id=uuid4(), is_superuser=True)
    assert ctx.has_permission("anything")
    assert ctx.can_access_district(uuid4())


def test_auth_context_district_scope() -> None:
    district_id = uuid4()
    ctx = AuthContext(
        user_id=uuid4(),
        allowed_district_ids=(district_id,),
    )
    assert ctx.can_access_district(district_id)
    assert not ctx.can_access_district(uuid4())


def test_error_codes() -> None:
    err = NotFoundError("missing")
    assert err.code == "NOT_FOUND"
    assert err.http_status == 404
    forbidden = ForbiddenError("nope")
    assert forbidden.http_status == 403
