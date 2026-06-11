"""Add Availity credentials to billing_providers

Revision ID: 0039
Revises: 0038
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS availity_client_id_encrypted TEXT"
    )
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS availity_client_secret_encrypted TEXT"
    )
    op.execute(
        "ALTER TABLE public.billing_providers"
        " ADD COLUMN IF NOT EXISTS availity_npi VARCHAR(10)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.billing_providers DROP COLUMN IF EXISTS availity_npi")
    op.execute("ALTER TABLE public.billing_providers DROP COLUMN IF EXISTS availity_client_secret_encrypted")
    op.execute("ALTER TABLE public.billing_providers DROP COLUMN IF EXISTS availity_client_id_encrypted")
