"""Add UHC API credentials to users table

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("uhc_client_id_encrypted", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("uhc_client_secret_encrypted", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "uhc_client_secret_encrypted", schema="public")
    op.drop_column("users", "uhc_client_id_encrypted", schema="public")
