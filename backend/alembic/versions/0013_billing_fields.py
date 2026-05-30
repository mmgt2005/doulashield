"""Add billing fields to users and create escrow_deductions table

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.Text(), nullable=True), schema="public")
    op.add_column("users", sa.Column("escrow_agreed_at", sa.DateTime(timezone=True), nullable=True), schema="public")
    op.add_column("users", sa.Column("escrow_agreement_version", sa.String(16), nullable=True), schema="public")
    op.add_column("users", sa.Column("deposit_paid", sa.Boolean(), server_default="false", nullable=False), schema="public")
    op.add_column("users", sa.Column("deposit_paid_at", sa.DateTime(timezone=True), nullable=True), schema="public")
    op.add_column("users", sa.Column("escrow_balance_remaining", sa.Numeric(10, 2), server_default="400.00", nullable=False), schema="public")
    op.add_column("users", sa.Column("stripe_subscription_id", sa.Text(), nullable=True), schema="public")
    op.add_column("users", sa.Column("subscription_status", sa.String(32), nullable=True), schema="public")

    op.create_table(
        "escrow_deductions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("remittance_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount_deducted", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_before", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(10, 2), nullable=False),
        sa.Column("stripe_charge_id", sa.Text(), nullable=True),
        sa.Column("deducted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="public",
    )
    op.execute("ALTER TABLE public.escrow_deductions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("escrow_deductions", schema="public")
    op.drop_column("users", "subscription_status", schema="public")
    op.drop_column("users", "stripe_subscription_id", schema="public")
    op.drop_column("users", "escrow_balance_remaining", schema="public")
    op.drop_column("users", "deposit_paid_at", schema="public")
    op.drop_column("users", "deposit_paid", schema="public")
    op.drop_column("users", "escrow_agreement_version", schema="public")
    op.drop_column("users", "escrow_agreed_at", schema="public")
    op.drop_column("users", "stripe_customer_id", schema="public")
