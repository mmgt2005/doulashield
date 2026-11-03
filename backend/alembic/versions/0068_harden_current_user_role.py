"""Harden current_user_role function.

Two Supabase Security Advisor warnings:
1. Function Search Path Mutable: add SET search_path = public so the
   function cannot be hijacked by a shadowing schema.
2. Public Can Execute SECURITY DEFINER Function: revoke EXECUTE from
   the anon role. The authenticated role keeps EXECUTE because the RLS
   policies on patients/soap_notes/prenatal_postnatal_logs/birth_logs/
   claims/prior_authorizations/remittances call this function at query time.

Revision ID: 0068
Revises: 0067
Create Date: 2026-11-03
"""
from __future__ import annotations

from alembic import op

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix 1: pin search_path so the function cannot be shadowed
    op.execute("""
        CREATE OR REPLACE FUNCTION public.current_user_role()
        RETURNS TEXT AS $$
          SELECT role FROM public.users WHERE id = auth.uid();
        $$ LANGUAGE sql SECURITY DEFINER STABLE SET search_path = public
    """)
    # Fix 2: revoke anon execute (authenticated keeps it for RLS policies)
    op.execute("REVOKE EXECUTE ON FUNCTION public.current_user_role() FROM anon")


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.current_user_role()
        RETURNS TEXT AS $$
          SELECT role FROM public.users WHERE id = auth.uid();
        $$ LANGUAGE sql SECURITY DEFINER STABLE
    """)
    op.execute("GRANT EXECUTE ON FUNCTION public.current_user_role() TO anon")
