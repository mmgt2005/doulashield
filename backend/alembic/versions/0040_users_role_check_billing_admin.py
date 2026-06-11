"""Add billing_admin to users_role_check constraint

Revision ID: 0040
Revises: 0039
Create Date: 2026-06-11
"""
from __future__ import annotations

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check")
    op.execute(
        "ALTER TABLE public.users ADD CONSTRAINT users_role_check"
        " CHECK (role IN ('provider', 'admin', 'billing_admin'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check")
    op.execute(
        "ALTER TABLE public.users ADD CONSTRAINT users_role_check"
        " CHECK (role IN ('provider', 'admin'))"
    )
