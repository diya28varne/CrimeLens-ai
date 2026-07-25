"""Add socio-economic correlation tables."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_socio_economic"
down_revision: str | None = "0001_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "socio_economic_indicators",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("district_id", sa.UUID(), sa.ForeignKey("districts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("indicator_code", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("district_id", "year", "indicator_code", name="uq_socio_indicator"),
    )
    op.create_index("ix_socio_indicators_year_code", "socio_economic_indicators", ["year", "indicator_code"])
    op.create_index("ix_socio_indicators_district_year", "socio_economic_indicators", ["district_id", "year"])

    op.create_table(
        "district_crime_metrics",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("district_id", sa.UUID(), sa.ForeignKey("districts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("incident_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("crime_rate_per_100k", sa.Float(), nullable=False),
        sa.Column("high_severity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("district_id", "year", name="uq_district_crime_year"),
    )
    op.create_index("ix_district_crime_metrics_year", "district_crime_metrics", ["year"])
    op.create_index("ix_district_crime_metrics_rate", "district_crime_metrics", ["crime_rate_per_100k"])

    op.create_table(
        "socio_crime_correlations",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("indicator_code", sa.String(length=64), nullable=False),
        sa.Column("crime_metric", sa.String(length=64), nullable=False),
        sa.Column("coefficient", sa.Float(), nullable=False),
        sa.Column("abs_coefficient", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False, server_default="pearson"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("year", "indicator_code", "crime_metric", "method", name="uq_socio_crime_corr"),
    )
    op.create_index("ix_socio_corr_year_abs", "socio_crime_correlations", ["year", "abs_coefficient"])


def downgrade() -> None:
    op.drop_index("ix_socio_corr_year_abs", table_name="socio_crime_correlations")
    op.drop_table("socio_crime_correlations")
    op.drop_index("ix_district_crime_metrics_rate", table_name="district_crime_metrics")
    op.drop_index("ix_district_crime_metrics_year", table_name="district_crime_metrics")
    op.drop_table("district_crime_metrics")
    op.drop_index("ix_socio_indicators_district_year", table_name="socio_economic_indicators")
    op.drop_index("ix_socio_indicators_year_code", table_name="socio_economic_indicators")
    op.drop_table("socio_economic_indicators")
