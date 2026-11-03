"""Enable RLS on alembic_version.

alembic_version was omitted from migration 0066 (enable_rls_all_tables).
With RLS on and no policies the anon/authenticated roles cannot access
this table through the PostgREST API. The superuser DATABASE_URL connection
Alembic uses bypasses RLS, so migration behaviour is unchanged.

Revision ID: 0067
Revises: 0066
Create Date: 2026-11-03
"""
from __future__ import annotations

from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")
