"""Add eligibility fields to patients and Availity credential fields to users

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-28
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS date_of_birth DATE")
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS eligibility_status VARCHAR(50)")
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS eligibility_checked_at TIMESTAMPTZ")

    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS npi VARCHAR(10)")
    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS availity_client_id_encrypted TEXT")
    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS availity_client_secret_encrypted TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS availity_client_secret_encrypted")
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS availity_client_id_encrypted")
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS npi")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS eligibility_checked_at")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS eligibility_status")
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS date_of_birth")
