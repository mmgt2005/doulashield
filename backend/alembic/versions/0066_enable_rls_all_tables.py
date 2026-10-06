"""Enable Row-Level Security on all public tables.

Supabase exposes every table via its PostgREST API unless RLS is enabled.
With RLS on and no permissive policies, the anon and authenticated roles
are denied all access through the API. The application connects via the
postgres superuser role (DATABASE_URL), which bypasses RLS entirely, so
no application behaviour changes.

Revision ID: 0066
Revises: 0065
Create Date: 2026-10-06
"""
from __future__ import annotations

from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None

_TABLES = [
    "audit_logs",
    "billing_providers",
    "birth_logs",
    "claim_documents",
    "claim_error_codes",
    "claims",
    "enrollment_documents",
    "enrollment_services",
    "enrollment_tasks",
    "escrow_deductions",
    "leads",
    "password_reset_tokens",
    "patients",
    "prenatal_postnatal_logs",
    "prior_authorizations",
    "push_subscriptions",
    "refresh_tokens",
    "remittances",
    "soap_notes",
    "users",
    "visits",
]


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')
