"""Add is_demo flag to leads

Revision ID: 0055
Revises: 0054
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.leads
        ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.leads
        DROP COLUMN IF EXISTS is_demo
    """)
