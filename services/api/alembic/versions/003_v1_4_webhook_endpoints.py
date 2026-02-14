"""Add webhook_endpoints table for v1.4.

Revision ID: 003
Revises: 002
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("events", sa.JSON(), server_default="[]"),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("description", sa.String(500), nullable=True),
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


def downgrade():
    op.drop_table("webhook_endpoints")
