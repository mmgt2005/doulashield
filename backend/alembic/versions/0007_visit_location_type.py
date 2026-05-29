"""Add location_type and alternate_location to visits; telehealth_link to users

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-28
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS location_type VARCHAR(20)")
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS alternate_location TEXT")
    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS telehealth_link TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS location_type")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS alternate_location")
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS telehealth_link")
