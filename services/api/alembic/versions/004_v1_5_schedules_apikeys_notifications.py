"""Add schedules, api_keys, notification_channels, compliance_mappings tables for v1.5/v1.6.

Revision ID: 004
Revises: 003
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    # ── Schedules ──
    op.create_table(
        "schedules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("scenario_id", sa.String(100), nullable=False),
        sa.Column("target_model", sa.String(200), nullable=False),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("compare_drift", sa.Boolean(), server_default="false"),
        sa.Column(
            "baseline_id",
            sa.String(),
            sa.ForeignKey("drift_baselines.id"),
            nullable=True,
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), server_default="0"),
        sa.Column(
            "user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── API Keys ──
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("key_hash", sa.String(64), nullable=False, index=True),
        sa.Column("prefix", sa.String(12), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("scopes", sa.JSON(), server_default='["read", "write"]'),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── Notification Channels ──
    op.create_table(
        "notification_channels",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "channel_type",
            sa.Enum("webhook", "slack", "email", "teams", name="channeltype"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("events", sa.JSON(), server_default="[]"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("failure_count", sa.Integer(), server_default="0"),
        sa.Column(
            "last_triggered_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── Compliance Mappings ──
    op.create_table(
        "compliance_mappings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("framework_id", sa.String(100), nullable=False, index=True),
        sa.Column("category_id", sa.String(100), nullable=False),
        sa.Column(
            "finding_id",
            sa.String(),
            sa.ForeignKey("findings.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )


def downgrade():
    op.drop_table("compliance_mappings")
    op.drop_table("notification_channels")
    op.drop_table("api_keys")
    op.drop_table("schedules")
    # Drop the channeltype enum (PostgreSQL only)
    sa.Enum(name="channeltype").drop(op.get_bind(), checkfirst=True)
