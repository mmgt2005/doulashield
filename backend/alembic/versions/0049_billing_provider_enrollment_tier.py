"""Add enrollment tier columns to billing_providers

Revision ID: 0049
Revises: 0048
Create Date: 2026-06-29
"""
from __future__ import annotations

from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.billing_providers
        ADD COLUMN IF NOT EXISTS enrollment_tier_enabled BOOLEAN NOT NULL DEFAULT false,
        ADD COLUMN IF NOT EXISTS enrollment_tier_stripe_item_id TEXT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.billing_providers
        DROP COLUMN IF EXISTS enrollment_tier_stripe_item_id,
        DROP COLUMN IF EXISTS enrollment_tier_enabled
    """)
