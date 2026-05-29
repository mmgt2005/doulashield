"""Add address/location to patients and start-visit fields to visits

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-28
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS address TEXT")
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION")
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION")

    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS visit_started_at TIMESTAMPTZ")
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS provider_latitude DOUBLE PRECISION")
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS provider_longitude DOUBLE PRECISION")


def downgrade() -> None:
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS provider_longitude")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS provider_latitude")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS visit_started_at")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS longitude")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS latitude")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS address")
