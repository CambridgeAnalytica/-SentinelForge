"""Add comparison_id, audit_id to attack_runs; create scoring_rubrics table.

Revision ID: 007
Revises: 006
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    # Add comparison_id and audit_id to attack_runs
    op.add_column(
        "attack_runs",
        sa.Column("comparison_id", sa.String(), nullable=True),
    )
    op.add_column(
        "attack_runs",
        sa.Column("audit_id", sa.String(), nullable=True),
    )
    op.create_index("ix_attack_runs_comparison_id", "attack_runs", ["comparison_id"])
    op.create_index("ix_attack_runs_audit_id", "attack_runs", ["audit_id"])

    # Create scoring_rubrics table
    op.create_table(
        "scoring_rubrics",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rules", sa.JSON(), server_default="{}"),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade():
    op.drop_table("scoring_rubrics")
    op.drop_index("ix_attack_runs_audit_id", "attack_runs")
    op.drop_index("ix_attack_runs_comparison_id", "attack_runs")
    op.drop_column("attack_runs", "audit_id")
    op.drop_column("attack_runs", "comparison_id")
