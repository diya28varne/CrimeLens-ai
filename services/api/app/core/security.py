"""Password hashing and JWT helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.settings import Settings

_password_hasher = PasswordHasher()

ACCESS_COOKIE = "cl_access"
REFRESH_COOKIE = "cl_refresh"


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(
    *,
    settings: Settings,
    user_id: UUID,
    roles: list[str],
    permissions: list[str],
    session_id: UUID,
) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "roles": roles,
        "permissions": permissions,
        "type": "access",
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, expires_at


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
