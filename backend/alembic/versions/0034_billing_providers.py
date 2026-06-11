"""billing_providers table and billing_provider_id on users

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("group_npi", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("zip", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("subscription_status", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.execute("ALTER TABLE public.billing_providers ENABLE ROW LEVEL SECURITY")

    op.add_column(
        "users",
        sa.Column(
            "billing_provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.billing_providers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "billing_provider_id", schema="public")
    op.drop_table("billing_providers", schema="public")
