"""Add leads table

Revision ID: 0047
Revises: 0046
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.leads (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source VARCHAR(32) NOT NULL DEFAULT 'manual',
            status VARCHAR(32) NOT NULL DEFAULT 'new',
            first_name VARCHAR(255) NOT NULL DEFAULT '',
            last_name VARCHAR(255) NOT NULL DEFAULT '',
            email VARCHAR(255) NOT NULL DEFAULT '',
            phone VARCHAR(50),
            organization_name VARCHAR(255),
            provider_type VARCHAR(32) NOT NULL DEFAULT 'unknown',
            lead_data JSONB,
            notes TEXT,
            follow_up_at TIMESTAMPTZ,
            assigned_to UUID REFERENCES public.users(id) ON DELETE SET NULL,
            converted_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.leads")
