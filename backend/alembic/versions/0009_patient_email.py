"""Add email column to patients

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-29
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS email TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS email")
