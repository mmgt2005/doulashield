"""Add caqh_last_attested_on to users

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("caqh_last_attested_on", sa.Date(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "caqh_last_attested_on", schema="public")
