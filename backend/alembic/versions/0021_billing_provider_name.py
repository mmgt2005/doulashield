"""Add billing_provider_name to users

Revision ID: 0021
Revises: 0020
"""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("billing_provider_name", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "billing_provider_name", schema="public")
