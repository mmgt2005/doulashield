"""Add encrypted DOB and tax-ID columns to users for enrollment

Revision ID: 0048
Revises: 0047
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.users
        ADD COLUMN IF NOT EXISTS provider_dob_encrypted TEXT,
        ADD COLUMN IF NOT EXISTS enrollment_tax_id_encrypted TEXT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.users
        DROP COLUMN IF EXISTS enrollment_tax_id_encrypted,
        DROP COLUMN IF EXISTS provider_dob_encrypted
    """)
