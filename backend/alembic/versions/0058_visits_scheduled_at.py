"""add scheduled_at to visits

Revision ID: 0058
Revises: 0057
Create Date: 2026-07-07
"""
from alembic import op

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.visits
        ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP WITH TIME ZONE
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_visits_provider_scheduled_at
        ON public.visits (provider_id, scheduled_at)
        WHERE scheduled_at IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_visits_provider_scheduled_at")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS scheduled_at")
