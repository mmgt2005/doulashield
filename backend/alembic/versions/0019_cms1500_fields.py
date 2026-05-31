"""Add CMS 1500 fields: patient other insurance/referring name, provider SSN/signature."""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("referring_provider_name", sa.String(100), nullable=True),
        schema="public",
    )
    op.add_column(
        "patients",
        sa.Column("has_other_insurance", sa.Boolean(), server_default="false", nullable=False),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("provider_ssn_encrypted", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("provider_signature_path", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "provider_signature_path", schema="public")
    op.drop_column("users", "provider_ssn_encrypted", schema="public")
    op.drop_column("patients", "has_other_insurance", schema="public")
    op.drop_column("patients", "referring_provider_name", schema="public")
