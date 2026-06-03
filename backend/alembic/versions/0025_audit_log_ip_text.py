"""Change audit_logs.ip_address from INET to TEXT

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-03
"""
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # INET is too strict — rejects non-IP strings like "unknown" or "scheduler".
    # TEXT stores any value and is sufficient since we never do IP-range queries.
    op.execute(
        "ALTER TABLE public.audit_logs ALTER COLUMN ip_address TYPE TEXT USING ip_address::TEXT"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE public.audit_logs ALTER COLUMN ip_address TYPE INET USING ip_address::INET"
    )
