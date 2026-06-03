"""Add promise_last_enrolled_on to users

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-03
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS promise_last_enrolled_on DATE NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.users DROP COLUMN IF EXISTS promise_last_enrolled_on"
    )
