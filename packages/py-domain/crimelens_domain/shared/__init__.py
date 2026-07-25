"""Shared primitives: errors, result types, identifiers."""

from crimelens_domain.shared.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)
from crimelens_domain.shared.types import EntityId

__all__ = [
    "AppError",
    "ConflictError",
    "EntityId",
    "ForbiddenError",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationAppError",
]
