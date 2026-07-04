"""Add is_executive flag to users

Revision ID: 0054
Revises: 0053
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.users
        ADD COLUMN IF NOT EXISTS is_executive BOOLEAN NOT NULL DEFAULT false
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.users
        DROP COLUMN IF EXISTS is_executive
    """)
