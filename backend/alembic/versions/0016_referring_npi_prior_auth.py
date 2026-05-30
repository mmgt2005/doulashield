"""Add referring_provider_npi to patients and prior_auth_number to visits

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("referring_provider_npi", sa.String(10), nullable=True),
        schema="public",
    )
    op.add_column(
        "visits",
        sa.Column("prior_auth_number", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("visits", "prior_auth_number", schema="public")
    op.drop_column("patients", "referring_provider_npi", schema="public")
