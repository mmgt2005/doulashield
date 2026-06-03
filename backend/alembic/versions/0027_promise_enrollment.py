"""Add promise_last_enrolled_on to users

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("promise_last_enrolled_on", sa.Date(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "promise_last_enrolled_on", schema="public")
