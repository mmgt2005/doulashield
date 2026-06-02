"""Add denial_reason and remittance_id to claims

Revision ID: 0024
Revises: 0023
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "claims",
        sa.Column("denial_reason", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "claims",
        sa.Column("remittance_id", UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "fk_claims_remittance_id",
        "claims",
        "remittances",
        ["remittance_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.create_index(
        "idx_claims_remittance_id",
        "claims",
        ["remittance_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_claims_remittance_id",
        "claims",
        schema="public",
        type_="foreignkey",
    )
    op.drop_index("idx_claims_remittance_id", table_name="claims", schema="public")
    op.drop_column("claims", "remittance_id", schema="public")
    op.drop_column("claims", "denial_reason", schema="public")
