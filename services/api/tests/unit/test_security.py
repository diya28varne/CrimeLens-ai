"""Security helper unit tests."""

from uuid import uuid4

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.settings import Settings


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("ChangeMe123!")
    assert verify_password(hashed, "ChangeMe123!")
    assert not verify_password(hashed, "wrong-password")


def test_token_hash_stable() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abcd")


def test_access_token_roundtrip() -> None:
    settings = Settings(JWT_SECRET="test-secret-key-at-least-32-bytes!!")
    user_id = uuid4()
    session_id = uuid4()
    token, expires = create_access_token(
        settings=settings,
        user_id=user_id,
        roles=["admin"],
        permissions=["incident:read"],
        session_id=session_id,
    )
    payload = decode_access_token(settings, token)
    assert payload["sub"] == str(user_id)
    assert payload["sid"] == str(session_id)
    assert payload["roles"] == ["admin"]
    assert expires.tzinfo is not None
