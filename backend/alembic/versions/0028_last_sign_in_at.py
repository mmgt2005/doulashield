"""add last_sign_in_at to users

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-03
"""

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_sign_in_at TIMESTAMPTZ NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.users DROP COLUMN IF EXISTS last_sign_in_at"
    )
