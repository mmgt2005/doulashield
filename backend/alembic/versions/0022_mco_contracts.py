"""Add mco_contracts_json to users

Revision ID: 0022
Revises: 0021
"""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("mco_contracts_json", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "mco_contracts_json", schema="public")
