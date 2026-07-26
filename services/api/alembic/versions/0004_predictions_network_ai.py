"""Predictions, hotspots, network persons, AI conversations."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography, Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0004_predictions_network_ai"
down_revision: str | None = "0003_incidents_postgis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    model_task = sa.Enum(
        "forecast", "risk", "hotspot", "repeat_offender", "trend", name="model_task"
    )
    model_status = sa.Enum(
        "training", "shadow", "production", "retired", "failed", name="model_status"
    )
    prediction_scope_type = sa.Enum(
        "state", "district", "station", "grid_cell", "hotspot", name="prediction_scope_type"
    )
    prediction_metric = sa.Enum(
        "incident_count", "risk_score", "hotspot_intensity", name="prediction_metric"
    )
    hotspot_method = sa.Enum(
        "hdbscan", "grid_density", "kde", "other", name="hotspot_method"
    )
    person_link_type = sa.Enum(
        "co_accused", "associate", "same_address", "family", "other", name="person_link_type"
    )
    person_link_origin = sa.Enum("derived", "curated", name="person_link_origin")
    message_role = sa.Enum("system", "user", "assistant", "tool", name="message_role")

    op.create_table(
        "model_registry",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("model_code", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("task", model_task, nullable=False),
        sa.Column("algorithm", sa.String(64), nullable=False),
        sa.Column("status", model_status, nullable=False, server_default="training"),
        sa.Column("train_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("train_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("feature_list", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("model_code", "model_version", name="uq_model_code_version"),
    )

    op.create_table(
        "prediction_runs",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("model_id", sa.UUID(), sa.ForeignKey("model_registry.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scope_type", prediction_scope_type, nullable=False),
        sa.Column("metric", prediction_metric, nullable=False),
        sa.Column("horizon_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_prediction_runs_scope_metric_current",
        "prediction_runs",
        ["scope_type", "metric", "is_current"],
    )

    op.create_table(
        "prediction_values",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "prediction_run_id",
            sa.UUID(),
            sa.ForeignKey("prediction_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("district_id", sa.UUID(), sa.ForeignKey("districts.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "station_id",
            sa.UUID(),
            sa.ForeignKey("police_stations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("lower_bound", sa.Float(), nullable=True),
        sa.Column("upper_bound", sa.Float(), nullable=True),
        sa.Column("occurs_on", sa.Date(), nullable=True),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prediction_values_prediction_run_id", "prediction_values", ["prediction_run_id"])
    op.create_index("ix_prediction_values_run_value", "prediction_values", ["prediction_run_id", "value"])

    op.create_table(
        "explanation_artifacts",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "prediction_run_id",
            sa.UUID(),
            sa.ForeignKey("prediction_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prediction_value_id",
            sa.UUID(),
            sa.ForeignKey("prediction_values.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("shap_global", postgresql.JSONB(), nullable=True),
        sa.Column("shap_local", postgresql.JSONB(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_explanation_artifacts_run", "explanation_artifacts", ["prediction_run_id"])
    op.create_index("ix_explanation_artifacts_value", "explanation_artifacts", ["prediction_value_id"])

    op.create_table(
        "hotspot_runs",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("method", hotspot_method, nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("district_id", sa.UUID(), sa.ForeignKey("districts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "hotspot_features",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "hotspot_run_id",
            sa.UUID(),
            sa.ForeignKey("hotspot_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("incident_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("centroid", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_hotspot_features_run_id", "hotspot_features", ["hotspot_run_id"])
    op.create_index("ix_hotspot_features_run_rank", "hotspot_features", ["hotspot_run_id", "rank"])

    op.create_table(
        "persons",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("external_ref", sa.String(128), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("alias", sa.String(255), nullable=True),
        sa.Column("is_repeat_offender", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("risk_flags", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("external_ref"),
    )
    op.create_index("ix_persons_full_name", "persons", ["full_name"])
    op.execute(
        "CREATE INDEX ix_persons_repeat ON persons (is_repeat_offender) WHERE is_repeat_offender = true"
    )

    op.create_table(
        "person_links",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("person_a_id", sa.UUID(), sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_b_id", sa.UUID(), sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_type", person_link_type, nullable=False),
        sa.Column("origin", person_link_origin, nullable=False, server_default="derived"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column(
            "evidence_incident_id",
            sa.UUID(),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("person_a_id", "person_b_id", "link_type", name="uq_person_link"),
    )
    op.create_index("ix_person_links_a", "person_links", ["person_a_id"])
    op.create_index("ix_person_links_b", "person_links", ["person_b_id"])

    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="New conversation"),
        sa.Column("district_id", sa.UUID(), sa.ForeignKey("districts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id",
            sa.UUID(),
            sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("tool_traces", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
    op.drop_table("person_links")
    op.execute("DROP INDEX IF EXISTS ix_persons_repeat")
    op.drop_table("persons")
    op.drop_table("hotspot_features")
    op.drop_table("hotspot_runs")
    op.drop_table("explanation_artifacts")
    op.drop_table("prediction_values")
    op.drop_table("prediction_runs")
    op.drop_table("model_registry")
    for name in (
        "message_role",
        "person_link_origin",
        "person_link_type",
        "hotspot_method",
        "prediction_metric",
        "prediction_scope_type",
        "model_status",
        "model_task",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
