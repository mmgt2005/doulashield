"""Add provider_address and provider_phone to users table."""
import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("provider_address", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("provider_phone", sa.String(20), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "provider_phone", schema="public")
    op.drop_column("users", "provider_address", schema="public")
