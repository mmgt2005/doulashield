"""add ma589_signed_date to patients

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("ma589_signed_date", sa.Date(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("patients", "ma589_signed_date", schema="public")
