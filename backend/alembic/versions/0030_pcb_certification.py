"""add pcb_last_certified_on to users

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS pcb_last_certified_on DATE NULL"
    )


def downgrade() -> None:
    op.drop_column("users", "pcb_last_certified_on", schema="public")
