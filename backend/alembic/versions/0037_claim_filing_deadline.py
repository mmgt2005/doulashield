"""filing_deadline_date on claims

Revision ID: 0037
Revises: 0036
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "claims",
        sa.Column("filing_deadline_date", sa.Date(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("claims", "filing_deadline_date", schema="public")
