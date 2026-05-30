"""Replace single county with multi-county JSON array

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "county", schema="public")
    op.add_column("users", sa.Column("counties", sa.Text(), nullable=True), schema="public")


def downgrade() -> None:
    op.drop_column("users", "counties", schema="public")
    op.add_column("users", sa.Column("county", sa.String(64), nullable=True), schema="public")
