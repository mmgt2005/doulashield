"""Add visit_ended_at to visits

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-29
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS visit_ended_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS visit_ended_at")
