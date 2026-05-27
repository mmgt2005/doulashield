"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String, nullable=False, unique=True),
        sa.Column("password_hash", sa.String, nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("full_name", sa.String, nullable=True),
        sa.Column("totp_secret", sa.String, nullable=True),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("role IN ('provider', 'admin')", name="users_role_check"),
        schema="public",
    )

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("token_hash", sa.String, nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )

    # ── patients ──────────────────────────────────────────────────────────────
    op.create_table(
        "patients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("name_encrypted", sa.Text, nullable=False),
        sa.Column("medicaid_id_encrypted", sa.Text, nullable=False),
        sa.Column("mco", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )

    # ── soap_notes ────────────────────────────────────────────────────────────
    op.create_table(
        "soap_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("public.patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("subjective", sa.Text, nullable=True),
        sa.Column("objective", sa.Text, nullable=True),
        sa.Column("assessment", sa.Text, nullable=True),
        sa.Column("plan", sa.Text, nullable=True),
        sa.Column("visit_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )

    # ── prenatal_postnatal_logs ───────────────────────────────────────────────
    op.create_table(
        "prenatal_postnatal_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("public.patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("log_type", sa.Text, nullable=False),
        sa.Column("entry", sa.Text, nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("log_type IN ('prenatal', 'postnatal')", name="ppl_log_type_check"),
        schema="public",
    )

    # ── birth_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "birth_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("public.patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("birth_date", sa.Date, nullable=False),
        sa.Column("birth_time", sa.Time, nullable=True),
        sa.Column("birth_location", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=True),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("extra_context", JSONB, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )

    # Immutability: PostgreSQL rules block UPDATE and DELETE at the DB layer
    op.execute(
        "CREATE RULE audit_logs_no_update AS ON UPDATE TO public.audit_logs DO INSTEAD NOTHING"
    )
    op.execute(
        "CREATE RULE audit_logs_no_delete AS ON DELETE TO public.audit_logs DO INSTEAD NOTHING"
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    op.create_index("idx_patients_provider_id", "patients", ["provider_id"], schema="public")
    op.create_index("idx_soap_notes_patient_id", "soap_notes", ["patient_id"], schema="public")
    op.create_index("idx_soap_notes_provider_id", "soap_notes", ["provider_id"], schema="public")
    op.create_index("idx_ppl_patient_id", "prenatal_postnatal_logs", ["patient_id"], schema="public")
    op.create_index("idx_birth_logs_patient_id", "birth_logs", ["patient_id"], schema="public")
    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"], schema="public")
    op.create_index("idx_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"], schema="public")
    op.create_index("idx_audit_logs_timestamp", "audit_logs", ["timestamp"], schema="public")

    # ── Row Level Security ────────────────────────────────────────────────────
    for table in ("patients", "soap_notes", "prenatal_postnatal_logs", "birth_logs", "audit_logs"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE OR REPLACE FUNCTION public.current_user_role()
        RETURNS TEXT AS $$
          SELECT role FROM public.users WHERE id = auth.uid();
        $$ LANGUAGE sql SECURITY DEFINER STABLE
    """)

    for table in ("patients", "soap_notes", "prenatal_postnatal_logs", "birth_logs"):
        op.execute(f"""
            CREATE POLICY "providers_own_{table}" ON public.{table}
            FOR ALL USING (
                provider_id = auth.uid()
                OR public.current_user_role() = 'admin'
            )
        """)

    op.execute("""
        CREATE POLICY "audit_insert" ON public.audit_logs
        FOR INSERT WITH CHECK (TRUE)
    """)
    op.execute("""
        CREATE POLICY "audit_read_admin_only" ON public.audit_logs
        FOR SELECT USING (public.current_user_role() = 'admin')
    """)


def downgrade() -> None:
    for table in ("patients", "soap_notes", "prenatal_postnatal_logs", "birth_logs", "audit_logs"):
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP RULE IF EXISTS audit_logs_no_delete ON public.audit_logs")
    op.execute("DROP RULE IF EXISTS audit_logs_no_update ON public.audit_logs")

    op.drop_table("audit_logs", schema="public")
    op.drop_table("birth_logs", schema="public")
    op.drop_table("prenatal_postnatal_logs", schema="public")
    op.drop_table("soap_notes", schema="public")
    op.drop_table("patients", schema="public")
    op.drop_table("refresh_tokens", schema="public")
    op.drop_table("users", schema="public")
    op.execute("DROP FUNCTION IF EXISTS public.current_user_role()")
