"""Add MA 91 signature fields to visits; contact_email and zipzign credentials to users

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-29
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS ma91_signed_at TIMESTAMPTZ")
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS ma91_signature_path TEXT")
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS ma91_signed_by_name TEXT")
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS ma91_zipzign_request_id TEXT")
    op.execute("ALTER TABLE public.visits ADD COLUMN IF NOT EXISTS ma91_status VARCHAR(20)")
    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS contact_email TEXT")
    op.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS zipzign_api_key_encrypted TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS ma91_signed_at")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS ma91_signature_path")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS ma91_signed_by_name")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS ma91_zipzign_request_id")
    op.execute("ALTER TABLE public.visits DROP COLUMN IF EXISTS ma91_status")
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS contact_email")
    op.execute("ALTER TABLE public.users DROP COLUMN IF EXISTS zipzign_api_key_encrypted")
