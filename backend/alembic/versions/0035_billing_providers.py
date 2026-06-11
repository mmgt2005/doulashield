"""billing_providers table and billing_provider_id on users

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-11
"""
from __future__ import annotations

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.billing_providers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            group_npi TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            phone TEXT,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            subscription_status VARCHAR(32),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
    """)
    op.execute("ALTER TABLE public.billing_providers ENABLE ROW LEVEL SECURITY")
    op.execute(
        "ALTER TABLE public.users"
        " ADD COLUMN IF NOT EXISTS billing_provider_id UUID"
        " REFERENCES public.billing_providers(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS billing_provider_id")
    op.execute("DROP TABLE IF EXISTS public.billing_providers")
