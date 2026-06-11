"""filing_deadline_date on claims

Revision ID: 0037
Revises: 0036
Create Date: 2026-06-11
"""
from __future__ import annotations

from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.claims ADD COLUMN IF NOT EXISTS filing_deadline_date DATE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.claims DROP COLUMN IF EXISTS filing_deadline_date")
