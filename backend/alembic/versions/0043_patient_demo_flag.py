"""Add is_demo flag to patients

Revision ID: 0043
Revises: 0042
Create Date: 2026-06-23
"""

from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS is_demo")
