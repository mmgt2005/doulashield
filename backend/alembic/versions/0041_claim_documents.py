"""Add claim_documents table for billing-admin-uploaded supporting files

Revision ID: 0041
Revises: 0040
Create Date: 2026-06-14
"""
from __future__ import annotations

from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.claim_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            claim_id UUID NOT NULL REFERENCES public.claims(id) ON DELETE CASCADE,
            uploaded_by UUID REFERENCES public.users(id),
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            document_type VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_claim_documents_claim_id "
        "ON public.claim_documents(claim_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.claim_documents")
