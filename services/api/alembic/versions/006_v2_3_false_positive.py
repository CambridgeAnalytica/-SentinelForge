"""Add false_positive column and analyst role.

Revision ID: 006
Revises: 005
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    # Add false_positive column to findings
    op.add_column(
        "findings",
        sa.Column(
            "false_positive", sa.Boolean(), server_default="false", nullable=False
        ),
    )

    # Add ANALYST value to userrole enum
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ANALYST'")


def downgrade():
    op.drop_column("findings", "false_positive")
    # Note: PostgreSQL doesn't support removing enum values
