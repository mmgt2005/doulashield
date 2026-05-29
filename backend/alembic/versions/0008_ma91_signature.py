"""Add MA 91 signature fields to visits; contact_email and zipzign credentials to users

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visits",
        sa.Column("ma91_signed_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "visits",
        sa.Column("ma91_signature_path", sa.Text, nullable=True),
        schema="public",
    )
    op.add_column(
        "visits",
        sa.Column("ma91_signed_by_name", sa.Text, nullable=True),
        schema="public",
    )
    op.add_column(
        "visits",
        sa.Column("ma91_zipzign_request_id", sa.Text, nullable=True),
        schema="public",
    )
    op.add_column(
        "visits",
        sa.Column("ma91_status", sa.String(20), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("contact_email", sa.Text, nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("zipzign_api_key_encrypted", sa.Text, nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("visits", "ma91_signed_at", schema="public")
    op.drop_column("visits", "ma91_signature_path", schema="public")
    op.drop_column("visits", "ma91_signed_by_name", schema="public")
    op.drop_column("visits", "ma91_zipzign_request_id", schema="public")
    op.drop_column("visits", "ma91_status", schema="public")
    op.drop_column("users", "contact_email", schema="public")
    op.drop_column("users", "zipzign_api_key_encrypted", schema="public")
