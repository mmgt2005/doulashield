"""Reconcile billing_providers table with application ORM schema

The billing_providers table was originally created via a manual Supabase SQL
migration that used a different column layout (npi/taxonomy_code/zip_code/
tax_id_encrypted). This migration aligns it with the schema expected by the
application: group_npi, zip, stripe columns, updated_at.

Revision ID: 0038
Revises: 0037
Create Date: 2026-06-11
"""
from __future__ import annotations

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename npi → group_npi (old schema had npi NOT NULL, new schema has group_npi nullable)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'billing_providers'
                  AND column_name = 'npi'
            ) THEN
                ALTER TABLE public.billing_providers RENAME COLUMN npi TO group_npi;
                ALTER TABLE public.billing_providers ALTER COLUMN group_npi DROP NOT NULL;
            END IF;
        END $$;
    """)

    # Rename zip_code → zip
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'billing_providers'
                  AND column_name = 'zip_code'
            ) THEN
                ALTER TABLE public.billing_providers RENAME COLUMN zip_code TO zip;
            END IF;
        END $$;
    """)

    # Drop columns not used by current ORM
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'billing_providers'
                  AND column_name = 'taxonomy_code'
            ) THEN
                ALTER TABLE public.billing_providers DROP COLUMN taxonomy_code;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'billing_providers'
                  AND column_name = 'tax_id_encrypted'
            ) THEN
                ALTER TABLE public.billing_providers DROP COLUMN tax_id_encrypted;
            END IF;
        END $$;
    """)

    # Add Stripe and updated_at columns required by the ORM model
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT"
    )
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT"
    )
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(32)"
    )
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"
    )

    # Ensure group_npi exists in case the table was freshly created by migration 0035
    # (IF NOT EXISTS guards make this safe either way)
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS group_npi TEXT"
    )
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS zip TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.billing_providers DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE public.billing_providers DROP COLUMN IF EXISTS subscription_status")
    op.execute("ALTER TABLE public.billing_providers DROP COLUMN IF EXISTS stripe_subscription_id")
    op.execute("ALTER TABLE public.billing_providers DROP COLUMN IF EXISTS stripe_customer_id")
