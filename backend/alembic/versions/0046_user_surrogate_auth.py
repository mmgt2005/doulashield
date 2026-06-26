"""Add surrogate_auth_signed_at to users

Revision ID: 0046
Revises: 0045
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.users "
        "ADD COLUMN IF NOT EXISTS surrogate_auth_signed_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS surrogate_auth_signed_at")
