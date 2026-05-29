"""Add source_image_path columns for document scanning

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.soap_notes ADD COLUMN IF NOT EXISTS source_image_path TEXT")
    op.execute("ALTER TABLE public.prenatal_postnatal_logs ADD COLUMN IF NOT EXISTS source_image_path TEXT")
    op.execute("ALTER TABLE public.birth_logs ADD COLUMN IF NOT EXISTS source_image_path TEXT")
    op.execute("ALTER TABLE public.patients ADD COLUMN IF NOT EXISTS medicaid_card_image_path TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE public.patients DROP COLUMN IF EXISTS medicaid_card_image_path")
    op.execute("ALTER TABLE public.birth_logs DROP COLUMN IF EXISTS source_image_path")
    op.execute("ALTER TABLE public.prenatal_postnatal_logs DROP COLUMN IF EXISTS source_image_path")
    op.execute("ALTER TABLE public.soap_notes DROP COLUMN IF EXISTS source_image_path")
