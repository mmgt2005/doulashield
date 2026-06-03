"""Add caqh_last_attested_on to users

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-03
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS caqh_last_attested_on DATE NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.users DROP COLUMN IF EXISTS caqh_last_attested_on"
    )
