"""Add assigned_to_billing_admin to enrollment_services

Revision ID: 0050
Revises: 0049
Create Date: 2026-06-30
"""
from __future__ import annotations

from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.enrollment_services
        ADD COLUMN IF NOT EXISTS assigned_to_billing_admin BOOLEAN NOT NULL DEFAULT false
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.enrollment_services
        DROP COLUMN IF EXISTS assigned_to_billing_admin
    """)
