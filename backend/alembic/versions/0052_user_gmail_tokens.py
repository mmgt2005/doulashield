"""Add Gmail OAuth token columns to users

Revision ID: 0052
Revises: 0051
Create Date: 2026-07-02
"""
from __future__ import annotations
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.users
        ADD COLUMN IF NOT EXISTS gmail_access_token_encrypted TEXT,
        ADD COLUMN IF NOT EXISTS gmail_refresh_token_encrypted TEXT,
        ADD COLUMN IF NOT EXISTS gmail_token_expiry TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS gmail_connected_email TEXT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.users
        DROP COLUMN IF EXISTS gmail_connected_email,
        DROP COLUMN IF EXISTS gmail_token_expiry,
        DROP COLUMN IF EXISTS gmail_refresh_token_encrypted,
        DROP COLUMN IF EXISTS gmail_access_token_encrypted
    """)
