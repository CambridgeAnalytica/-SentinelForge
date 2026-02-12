"""Initial schema — all v1.0 + v1.1 tables plus evidence hashing columns.

Revision ID: 001
Revises: None
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "operator", "viewer", name="userrole"),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- attack_runs ---
    op.create_table(
        "attack_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("scenario_id", sa.String(100), nullable=False, index=True),
        sa.Column("target_model", sa.String(200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="runstatus",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("progress", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("config", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("results", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
    )

    # --- findings (includes v1.2 evidence_hash columns) ---
    op.create_table(
        "findings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "run_id", sa.String(), sa.ForeignKey("attack_runs.id"), nullable=False
        ),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("critical", "high", "medium", "low", "info", name="severity"),
            nullable=False,
            server_default="info",
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mitre_technique", sa.String(50), nullable=True),
        sa.Column("evidence", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("evidence_hash", sa.String(64), nullable=True),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- reports ---
    op.create_table(
        "reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "run_id", sa.String(), sa.ForeignKey("attack_runs.id"), nullable=False
        ),
        sa.Column(
            "format",
            sa.Enum("html", "pdf", "jsonl", name="reportformat"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- probe_modules ---
    op.create_table(
        "probe_modules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("version", sa.String(20), server_default="1.0.0"),
        sa.Column("config_schema", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- drift_baselines ---
    op.create_table(
        "drift_baselines",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("model_name", sa.String(200), nullable=False, index=True),
        sa.Column("test_suite", sa.String(100), server_default="default"),
        sa.Column("scores", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("prompt_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- drift_results ---
    op.create_table(
        "drift_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "baseline_id",
            sa.String(),
            sa.ForeignKey("drift_baselines.id"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("scores", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("deltas", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("drift_detected", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- supply_chain_scans ---
    op.create_table(
        "supply_chain_scans",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("model_source", sa.String(500), nullable=False),
        sa.Column("checks_requested", sa.JSON(), server_default=sa.text("'[]'")),
        sa.Column("results", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("risk_level", sa.String(50), server_default="unknown"),
        sa.Column("issues_found", sa.Integer(), server_default=sa.text("0")),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- backdoor_scans ---
    op.create_table(
        "backdoor_scans",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("model_source", sa.String(500), nullable=False),
        sa.Column("scan_type", sa.String(100), server_default="behavioral"),
        sa.Column("results", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("indicators_found", sa.Integer(), server_default=sa.text("0")),
        sa.Column("risk_level", sa.String(50), server_default="unknown"),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'")),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("backdoor_scans")
    op.drop_table("supply_chain_scans")
    op.drop_table("drift_results")
    op.drop_table("drift_baselines")
    op.drop_table("probe_modules")
    op.drop_table("reports")
    op.drop_table("findings")
    op.drop_table("attack_runs")
    op.drop_table("users")

    # Drop enums
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="runstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="severity").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="reportformat").drop(op.get_bind(), checkfirst=True)
