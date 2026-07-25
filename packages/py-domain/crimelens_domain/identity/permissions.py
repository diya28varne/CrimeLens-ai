"""Canonical permission codes for CrimeLens RBAC."""

from __future__ import annotations

from typing import Final

INCIDENT_READ: Final = "incident:read"
INCIDENT_WRITE: Final = "incident:write"
INCIDENT_INGEST: Final = "incident:ingest"
ANALYTICS_READ: Final = "analytics:read"
ANALYTICS_EXPORT: Final = "analytics:export"
PREDICTION_READ: Final = "prediction:read"
NETWORK_READ: Final = "network:read"
PERSON_READ_SENSITIVE: Final = "person:read_sensitive"
AI_CHAT: Final = "ai:chat"
AI_BRIEF: Final = "ai:brief"
DECISION_READ: Final = "decision:read"
DECISION_APPROVE: Final = "decision:approve"
ADMIN_USERS: Final = "admin:users"
ADMIN_AUDIT: Final = "admin:audit"
ADMIN_JOBS: Final = "admin:jobs"

ALL_PERMISSIONS: Final[tuple[str, ...]] = (
    INCIDENT_READ,
    INCIDENT_WRITE,
    INCIDENT_INGEST,
    ANALYTICS_READ,
    ANALYTICS_EXPORT,
    PREDICTION_READ,
    NETWORK_READ,
    PERSON_READ_SENSITIVE,
    AI_CHAT,
    AI_BRIEF,
    DECISION_READ,
    DECISION_APPROVE,
    ADMIN_USERS,
    ADMIN_AUDIT,
    ADMIN_JOBS,
)

PERMISSION_DESCRIPTIONS: Final[dict[str, str]] = {
    INCIDENT_READ: "Read incidents and spatial layers",
    INCIDENT_WRITE: "Create or update incidents",
    INCIDENT_INGEST: "Batch ingest incidents",
    ANALYTICS_READ: "Read dashboard and analytics",
    ANALYTICS_EXPORT: "Export analytics datasets",
    PREDICTION_READ: "Read predictions, hotspots, explanations",
    NETWORK_READ: "Read criminal network graphs",
    PERSON_READ_SENSITIVE: "Read sensitive person PII fields",
    AI_CHAT: "Use AI copilot chat",
    AI_BRIEF: "Generate AI command briefs",
    DECISION_READ: "Read patrol recommendations",
    DECISION_APPROVE: "Approve patrol plans",
    ADMIN_USERS: "Manage users and roles",
    ADMIN_AUDIT: "View audit logs",
    ADMIN_JOBS: "View and manage background jobs",
}
