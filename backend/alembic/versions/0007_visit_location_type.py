"""Add location_type and alternate_location to visits; telehealth_link to users

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visits",
        sa.Column("location_type", sa.String(20), nullable=True),
        schema="public",
    )
    op.add_column(
        "visits",
        sa.Column("alternate_location", sa.Text, nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("telehealth_link", sa.Text, nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("visits", "location_type", schema="public")
    op.drop_column("visits", "alternate_location", schema="public")
    op.drop_column("users", "telehealth_link", schema="public")
