"""Add is_demo flag to billing_providers

Revision ID: 0057
Revises: 0056
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.billing_providers
        ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.billing_providers
        DROP COLUMN IF EXISTS is_demo
    """)
