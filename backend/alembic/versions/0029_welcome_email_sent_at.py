"""add welcome_email_sent_at to users

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-03
"""

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS welcome_email_sent_at TIMESTAMPTZ NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.users DROP COLUMN IF EXISTS welcome_email_sent_at"
    )
