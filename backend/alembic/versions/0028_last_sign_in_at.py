"""add last_sign_in_at to users

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "last_sign_in_at", schema="public")
