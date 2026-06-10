"""Add billing_providers table and billing_provider_id on users

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-10
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.billing_providers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL,
            npi VARCHAR(10) NOT NULL,
            taxonomy_code VARCHAR(15),
            address TEXT,
            city VARCHAR(100),
            state VARCHAR(2),
            zip_code VARCHAR(10),
            phone VARCHAR(20),
            tax_id_encrypted TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS billing_provider_id UUID "
        "REFERENCES public.billing_providers(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS billing_provider_id")
    op.execute("DROP TABLE IF EXISTS public.billing_providers")
