"""Add reminder_60min_sent and reminder_30min_sent flags to visits.

Revision ID: 0065
Revises: 0064
Create Date: 2026-08-31
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visits",
        sa.Column("reminder_60min_sent", sa.Boolean(), nullable=False, server_default="false"),
        schema="public",
    )
    op.add_column(
        "visits",
        sa.Column("reminder_30min_sent", sa.Boolean(), nullable=False, server_default="false"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("visits", "reminder_30min_sent", schema="public")
    op.drop_column("visits", "reminder_60min_sent", schema="public")
