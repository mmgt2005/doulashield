"""Add is_demo flag to enrollment_services

Revision ID: 0056
Revises: 0055
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.enrollment_services
        ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.enrollment_services
        DROP COLUMN IF EXISTS is_demo
    """)
