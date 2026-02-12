"""Add agent_tests and synthetic_datasets tables for v1.3.

Revision ID: 002
Revises: 001
Create Date: 2026-02-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- agent_tests ---
    op.create_table(
        "agent_tests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "running", "completed", "failed", "cancelled", name="runstatus", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("results", sa.JSON(), server_default="{}"),
        sa.Column("risk_level", sa.String(50), server_default="unknown"),
        sa.Column("findings_count", sa.Integer(), server_default="0"),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- synthetic_datasets ---
    op.create_table(
        "synthetic_datasets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("seed_count", sa.Integer(), server_default="0"),
        sa.Column("mutations_applied", sa.JSON(), server_default="[]"),
        sa.Column("total_generated", sa.Integer(), server_default="0"),
        sa.Column(
            "status",
            sa.Enum("queued", "running", "completed", "failed", "cancelled", name="runstatus", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("results", sa.JSON(), server_default="{}"),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("synthetic_datasets")
    op.drop_table("agent_tests")
