"""Add zone and county to users

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("zone", sa.String(4), nullable=True), schema="public")
    op.add_column("users", sa.Column("county", sa.String(64), nullable=True), schema="public")


def downgrade() -> None:
    op.drop_column("users", "county", schema="public")
    op.drop_column("users", "zone", schema="public")
