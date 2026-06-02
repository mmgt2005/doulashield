"""Add visit_type and is_manual to claims

Revision ID: 0023
Revises: 0022
"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "claims",
        sa.Column("visit_type", sa.String(30), nullable=True),
        schema="public",
    )
    op.add_column(
        "claims",
        sa.Column("is_manual", sa.Boolean(), server_default="false", nullable=False),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("claims", "is_manual", schema="public")
    op.drop_column("claims", "visit_type", schema="public")
