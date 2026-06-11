"""managed_billing_provider_id on users for billing_admin role

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "managed_billing_provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.billing_providers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "managed_billing_provider_id", schema="public")
