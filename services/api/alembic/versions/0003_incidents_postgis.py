"""Incidents + PostGIS + offense taxonomy."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "0003_incidents_postgis"
down_revision: str | None = "0002_socio_economic"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    incident_status = sa.Enum(
        "reported",
        "registered",
        "under_investigation",
        "chargesheeted",
        "closed",
        "cancelled",
        name="incident_status",
    )
    incident_source = sa.Enum(
        "manual",
        "csv_ingest",
        "api_ingest",
        "seed",
        name="incident_source",
    )
    severity_level = sa.Enum(
        "low",
        "medium",
        "high",
        "critical",
        name="severity_level",
    )

    op.create_table(
        "offense_categories",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "offense_types",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "category_id",
            sa.UUID(),
            sa.ForeignKey("offense_categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("default_severity", severity_level, nullable=False, server_default="medium"),
        sa.Column("is_cognizable", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_offense_types_category_id", "offense_types", ["category_id"])

    op.create_table(
        "ingest_batches",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("source", incident_source, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("success_count", sa.Integer(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "incidents",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("external_ref", sa.String(length=128), nullable=True),
        sa.Column(
            "offense_type_id",
            sa.UUID(),
            sa.ForeignKey("offense_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "district_id",
            sa.UUID(),
            sa.ForeignKey("districts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "station_id",
            sa.UUID(),
            sa.ForeignKey("police_stations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", incident_status, nullable=False, server_default="reported"),
        sa.Column("severity", severity_level, nullable=False),
        sa.Column("source", incident_source, nullable=False, server_default="manual"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("location_accuracy_m", sa.Float(), nullable=True),
        sa.Column("address_text", sa.Text(), nullable=True),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "ingest_batch_id",
            sa.UUID(),
            sa.ForeignKey("ingest_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_index("ix_incidents_occurred_at", "incidents", ["occurred_at"])
    op.create_index("ix_incidents_station_occurred", "incidents", ["station_id", "occurred_at"])
    op.create_index("ix_incidents_district_occurred", "incidents", ["district_id", "occurred_at"])
    op.create_index("ix_incidents_offense_occurred", "incidents", ["offense_type_id", "occurred_at"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index(
        "ux_incidents_external_ref",
        "incidents",
        ["external_ref"],
        unique=True,
        postgresql_where=sa.text("external_ref IS NOT NULL"),
    )
    op.create_index(
        "ix_incidents_active",
        "incidents",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.execute("CREATE INDEX ix_incidents_location_gix ON incidents USING GIST (location)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_incidents_location_gix")
    op.drop_index("ix_incidents_active", table_name="incidents")
    op.drop_index("ux_incidents_external_ref", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_offense_occurred", table_name="incidents")
    op.drop_index("ix_incidents_district_occurred", table_name="incidents")
    op.drop_index("ix_incidents_station_occurred", table_name="incidents")
    op.drop_index("ix_incidents_occurred_at", table_name="incidents")
    op.drop_table("incidents")
    op.drop_table("ingest_batches")
    op.drop_index("ix_offense_types_category_id", table_name="offense_types")
    op.drop_table("offense_types")
    op.drop_table("offense_categories")

    sa.Enum(name="severity_level").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="incident_source").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="incident_status").drop(op.get_bind(), checkfirst=True)
