"""Add run_type to attack_runs; create calibration_runs table.

Revision ID: 008
Revises: 007
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    # Add run_type to attack_runs for distinguishing RAG/tool/multimodal evals
    op.add_column(
        "attack_runs",
        sa.Column(
            "run_type",
            sa.String(50),
            nullable=True,
            server_default="attack",
        ),
    )

    # Create calibration_runs table
    op.create_table(
        "calibration_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("target_model", sa.String(200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="calibration_run_status",
            ),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column("progress", sa.Float(), server_default="0.0"),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("results", sa.JSON(), server_default="{}"),
        sa.Column("recommended_threshold", sa.Float(), nullable=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("calibration_runs")
    op.drop_column("attack_runs", "run_type")
