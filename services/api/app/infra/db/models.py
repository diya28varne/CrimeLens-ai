"""SQLAlchemy ORM models for Identity, Org, Socio-economic, Incidents, ML, Network, AI."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base


class UserStatus(str, enum.Enum):
    active = "active"
    invited = "invited"
    disabled = "disabled"


class SessionStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserStatus.active,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    roles: Mapped[list[RoleModel]] = relationship(
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )
    jurisdictions: Mapped[list[UserJurisdictionModel]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    users: Mapped[list[UserModel]] = relationship(
        secondary="user_roles",
        back_populates="roles",
        lazy="selectin",
    )
    permissions: Mapped[list[PermissionModel]] = relationship(
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )


class PermissionModel(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    roles: Mapped[list[RoleModel]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )


class RolePermissionModel(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserRoleModel(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DistrictModel(Base):
    """Minimal district row so jurisdiction FKs resolve in Phase 2."""

    __tablename__ = "districts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    state_code: Mapped[str] = mapped_column(String(8), nullable=False, default="KA")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PoliceStationModel(Base):
    __tablename__ = "police_stations"
    __table_args__ = (UniqueConstraint("district_id", "code", name="uq_station_district_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserJurisdictionModel(Base):
    __tablename__ = "user_jurisdictions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "district_id",
            "station_id",
            name="uq_user_jurisdiction",
        ),
        Index("ix_user_jurisdictions_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=True
    )
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("police_stations.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[UserModel] = relationship(back_populates="jurisdictions")


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_user_status", "user_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SessionStatus.active,
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_inet: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SocioEconomicIndicatorModel(Base):
    __tablename__ = "socio_economic_indicators"
    __table_args__ = (
        UniqueConstraint("district_id", "year", "indicator_code", name="uq_socio_indicator"),
        Index("ix_socio_indicators_year_code", "year", "indicator_code"),
        Index("ix_socio_indicators_district_year", "district_id", "year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DistrictCrimeMetricModel(Base):
    __tablename__ = "district_crime_metrics"
    __table_args__ = (
        UniqueConstraint("district_id", "year", name="uq_district_crime_year"),
        Index("ix_district_crime_metrics_year", "year"),
        Index("ix_district_crime_metrics_rate", "crime_rate_per_100k"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    crime_rate_per_100k: Mapped[float] = mapped_column(Float, nullable=False)
    high_severity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SocioCrimeCorrelationModel(Base):
    __tablename__ = "socio_crime_correlations"
    __table_args__ = (
        UniqueConstraint(
            "year",
            "indicator_code",
            "crime_metric",
            "method",
            name="uq_socio_crime_corr",
        ),
        Index("ix_socio_corr_year_abs", "year", "abs_coefficient"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    crime_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    abs_coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False, default="pearson")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IncidentStatus(str, enum.Enum):
    reported = "reported"
    registered = "registered"
    under_investigation = "under_investigation"
    chargesheeted = "chargesheeted"
    closed = "closed"
    cancelled = "cancelled"


class IncidentSource(str, enum.Enum):
    manual = "manual"
    csv_ingest = "csv_ingest"
    api_ingest = "api_ingest"
    seed = "seed"


class SeverityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class OffenseCategoryModel(Base):
    __tablename__ = "offense_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OffenseTypeModel(Base):
    __tablename__ = "offense_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("offense_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    default_severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SeverityLevel.medium,
    )
    is_cognizable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class IngestBatchModel(Base):
    __tablename__ = "ingest_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[IncidentSource] = mapped_column(
        Enum(IncidentSource, name="incident_source", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class IncidentModel(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_station_occurred", "station_id", "occurred_at"),
        Index("ix_incidents_district_occurred", "district_id", "occurred_at"),
        Index("ix_incidents_offense_occurred", "offense_type_id", "occurred_at"),
        Index(
            "ux_incidents_external_ref",
            "external_ref",
            unique=True,
            postgresql_where=text("external_ref IS NOT NULL"),
        ),
        Index(
            "ix_incidents_active",
            "deleted_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    offense_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offense_types.id", ondelete="RESTRICT"), nullable=False
    )
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False
    )
    station_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("police_stations.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=IncidentStatus.reported,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source: Mapped[IncidentSource] = mapped_column(
        Enum(IncidentSource, name="incident_source", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=IncidentSource.manual,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    location_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    address_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ingest_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingest_batches.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ModelTask(str, enum.Enum):
    forecast = "forecast"
    risk = "risk"
    hotspot = "hotspot"
    repeat_offender = "repeat_offender"
    trend = "trend"


class ModelStatus(str, enum.Enum):
    training = "training"
    shadow = "shadow"
    production = "production"
    retired = "retired"
    failed = "failed"


class PredictionScopeType(str, enum.Enum):
    state = "state"
    district = "district"
    station = "station"
    grid_cell = "grid_cell"
    hotspot = "hotspot"


class PredictionMetric(str, enum.Enum):
    incident_count = "incident_count"
    risk_score = "risk_score"
    hotspot_intensity = "hotspot_intensity"


class HotspotMethod(str, enum.Enum):
    hdbscan = "hdbscan"
    grid_density = "grid_density"
    kde = "kde"
    other = "other"


class PersonLinkType(str, enum.Enum):
    co_accused = "co_accused"
    associate = "associate"
    same_address = "same_address"
    family = "family"
    other = "other"


class PersonLinkOrigin(str, enum.Enum):
    derived = "derived"
    curated = "curated"


class MessageRole(str, enum.Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ModelRegistryModel(Base):
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("model_code", "model_version", name="uq_model_code_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_code: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    task: Mapped[ModelTask] = mapped_column(
        Enum(ModelTask, name="model_task", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, name="model_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ModelStatus.training,
    )
    train_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    train_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    feature_list: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    artifact_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PredictionRunModel(Base):
    __tablename__ = "prediction_runs"
    __table_args__ = (
        Index("ix_prediction_runs_scope_metric_current", "scope_type", "metric", "is_current"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False
    )
    scope_type: Mapped[PredictionScopeType] = mapped_column(
        Enum(
            PredictionScopeType,
            name="prediction_scope_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    metric: Mapped[PredictionMetric] = mapped_column(
        Enum(
            PredictionMetric,
            name="prediction_metric",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    horizon_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PredictionValueModel(Base):
    __tablename__ = "prediction_values"
    __table_args__ = (Index("ix_prediction_values_run_value", "prediction_run_id", "value"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prediction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="SET NULL"), nullable=True
    )
    station_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("police_stations.id", ondelete="SET NULL"), nullable=True
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurs_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExplanationArtifactModel(Base):
    __tablename__ = "explanation_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prediction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prediction_value_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prediction_values.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    shap_global: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    shap_local: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HotspotRunModel(Base):
    __tablename__ = "hotspot_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    method: Mapped[HotspotMethod] = mapped_column(
        Enum(HotspotMethod, name="hotspot_method", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="SET NULL"), nullable=True
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class HotspotFeatureModel(Base):
    __tablename__ = "hotspot_features"
    __table_args__ = (Index("ix_hotspot_features_run_rank", "hotspot_run_id", "rank"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hotspot_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hotspot_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    centroid = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PersonModel(Base):
    __tablename__ = "persons"
    __table_args__ = (
        Index(
            "ix_persons_repeat",
            "is_repeat_offender",
            postgresql_where=text("is_repeat_offender = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_repeat_offender: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PersonLinkModel(Base):
    __tablename__ = "person_links"
    __table_args__ = (
        UniqueConstraint("person_a_id", "person_b_id", "link_type", name="uq_person_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    link_type: Mapped[PersonLinkType] = mapped_column(
        Enum(PersonLinkType, name="person_link_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    origin: Mapped[PersonLinkOrigin] = mapped_column(
        Enum(
            PersonLinkOrigin,
            name="person_link_origin",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PersonLinkOrigin.derived,
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
    )
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AiConversationModel(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New conversation")
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AiMessageModel(Base):
    __tablename__ = "ai_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tool_traces: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
