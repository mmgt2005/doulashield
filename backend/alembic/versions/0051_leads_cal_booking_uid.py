"""Add cal_booking_uid column to leads

Revision ID: 0051
Revises: 0050
Create Date: 2026-07-02
"""
from __future__ import annotations
from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.leads
        ADD COLUMN IF NOT EXISTS cal_booking_uid TEXT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.leads
        DROP COLUMN IF EXISTS cal_booking_uid
    """)
