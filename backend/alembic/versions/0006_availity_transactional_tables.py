"""Add claims, prior_authorizations, and remittances tables for Availity integration

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── claims ────────────────────────────────────────────────────────────────
    op.create_table(
        "claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("public.patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("availity_claim_id", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("service_date", sa.Date, nullable=True),
        sa.Column("billed_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("payer_id", sa.Text, nullable=True),
        sa.Column("claim_data", JSONB, nullable=True),
        sa.Column("raw_response", JSONB, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )
    op.create_index("idx_claims_patient_id", "claims", ["patient_id"], schema="public")
    op.create_index("idx_claims_provider_id", "claims", ["provider_id"], schema="public")
    op.execute("ALTER TABLE public.claims ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY "providers_own_claims" ON public.claims
        FOR ALL USING (
            provider_id = auth.uid()
            OR public.current_user_role() = 'admin'
        )
    """)

    # ── prior_authorizations ─────────────────────────────────────────────────
    op.create_table(
        "prior_authorizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("public.patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("availity_auth_id", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("service_type", sa.Text, nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("auth_data", JSONB, nullable=True),
        sa.Column("raw_response", JSONB, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )
    op.create_index("idx_prior_auths_patient_id", "prior_authorizations", ["patient_id"], schema="public")
    op.create_index("idx_prior_auths_provider_id", "prior_authorizations", ["provider_id"], schema="public")
    op.execute("ALTER TABLE public.prior_authorizations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY "providers_own_prior_authorizations" ON public.prior_authorizations
        FOR ALL USING (
            provider_id = auth.uid()
            OR public.current_user_role() = 'admin'
        )
    """)

    # ── remittances ───────────────────────────────────────────────────────────
    op.create_table(
        "remittances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("availity_remit_id", sa.Text, nullable=True, unique=True),
        sa.Column("check_number", sa.Text, nullable=True),
        sa.Column("payer_id", sa.Text, nullable=True),
        sa.Column("payment_date", sa.Date, nullable=True),
        sa.Column("total_payment", sa.Numeric(10, 2), nullable=True),
        sa.Column("raw_response", JSONB, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="public",
    )
    op.create_index("idx_remittances_provider_id", "remittances", ["provider_id"], schema="public")
    op.execute("ALTER TABLE public.remittances ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY "providers_own_remittances" ON public.remittances
        FOR ALL USING (
            provider_id = auth.uid()
            OR public.current_user_role() = 'admin'
        )
    """)


def downgrade() -> None:
    op.drop_index("idx_remittances_provider_id", table_name="remittances", schema="public")
    op.drop_table("remittances", schema="public")

    op.drop_index("idx_prior_auths_provider_id", table_name="prior_authorizations", schema="public")
    op.drop_index("idx_prior_auths_patient_id", table_name="prior_authorizations", schema="public")
    op.drop_table("prior_authorizations", schema="public")

    op.drop_index("idx_claims_provider_id", table_name="claims", schema="public")
    op.drop_index("idx_claims_patient_id", table_name="claims", schema="public")
    op.drop_table("claims", schema="public")
