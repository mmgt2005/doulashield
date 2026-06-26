"""Add stage column to enrollment_services

Revision ID: 0045
Revises: 0044
Create Date: 2026-06-26
"""
from __future__ import annotations

from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public.enrollment_services "
        "ADD COLUMN IF NOT EXISTS stage VARCHAR(30) NOT NULL DEFAULT 'pcb'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.enrollment_services DROP COLUMN IF EXISTS stage")
