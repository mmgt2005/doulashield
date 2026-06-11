"""managed_billing_provider_id on users for billing_admin role

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-11
"""
from __future__ import annotations

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.users"
        " ADD COLUMN IF NOT EXISTS managed_billing_provider_id UUID"
        " REFERENCES public.billing_providers(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS managed_billing_provider_id")
