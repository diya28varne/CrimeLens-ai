"""Built-in role codes and default permission grants."""

from __future__ import annotations

from typing import Final

from crimelens_domain.identity import permissions as P

ROLE_ADMIN: Final = "admin"
ROLE_SP: Final = "sp"
ROLE_SHO: Final = "sho"
ROLE_ANALYST: Final = "analyst"
ROLE_CONTROL_ROOM: Final = "control_room"

ALL_ROLES: Final[tuple[str, ...]] = (
    ROLE_ADMIN,
    ROLE_SP,
    ROLE_SHO,
    ROLE_ANALYST,
    ROLE_CONTROL_ROOM,
)

ROLE_NAMES: Final[dict[str, str]] = {
    ROLE_ADMIN: "System Administrator",
    ROLE_SP: "Superintendent of Police",
    ROLE_SHO: "Station House Officer",
    ROLE_ANALYST: "Crime Analyst",
    ROLE_CONTROL_ROOM: "Control Room Operator",
}

ROLE_PERMISSIONS: Final[dict[str, tuple[str, ...]]] = {
    ROLE_ADMIN: P.ALL_PERMISSIONS,
    ROLE_SP: (
        P.INCIDENT_READ,
        P.ANALYTICS_READ,
        P.ANALYTICS_EXPORT,
        P.PREDICTION_READ,
        P.NETWORK_READ,
        P.AI_CHAT,
        P.AI_BRIEF,
        P.DECISION_READ,
        P.DECISION_APPROVE,
    ),
    ROLE_SHO: (
        P.INCIDENT_READ,
        P.ANALYTICS_READ,
        P.PREDICTION_READ,
        P.AI_CHAT,
        P.DECISION_READ,
    ),
    ROLE_ANALYST: (
        P.INCIDENT_READ,
        P.INCIDENT_INGEST,
        P.ANALYTICS_READ,
        P.ANALYTICS_EXPORT,
        P.PREDICTION_READ,
        P.NETWORK_READ,
        P.PERSON_READ_SENSITIVE,
        P.AI_CHAT,
        P.AI_BRIEF,
        P.DECISION_READ,
    ),
    ROLE_CONTROL_ROOM: (
        P.INCIDENT_READ,
        P.ANALYTICS_READ,
        P.PREDICTION_READ,
        P.AI_CHAT,
    ),
}
