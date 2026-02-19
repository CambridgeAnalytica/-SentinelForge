"""Add findings dedup columns and audit_logs table for v2.1.

Revision ID: 005
Revises: 004
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    # ── Findings deduplication columns ──
    op.add_column(
        "findings",
        sa.Column("fingerprint", sa.String(64), nullable=True, index=True),
    )
    op.add_column(
        "findings",
        sa.Column("is_new", sa.Boolean(), server_default="true", nullable=True),
    )
    op.create_index("ix_findings_fingerprint", "findings", ["fingerprint"])

    # ── Audit Logs table ──
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("action", sa.String(255), nullable=False, index=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True, index=True),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )


def downgrade():
    op.drop_table("audit_logs")
    op.drop_index("ix_findings_fingerprint", table_name="findings")
    op.drop_column("findings", "is_new")
    op.drop_column("findings", "fingerprint")
