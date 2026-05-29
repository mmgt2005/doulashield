"""Add claims, prior_authorizations, and remittances tables for Availity integration

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-28
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── claims ────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.claims (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id        UUID NOT NULL REFERENCES public.patients(id),
            provider_id       UUID NOT NULL REFERENCES public.users(id),
            availity_claim_id TEXT,
            status            VARCHAR(50),
            service_date      DATE,
            billed_amount     NUMERIC(10,2),
            paid_amount       NUMERIC(10,2),
            payer_id          TEXT,
            claim_data        JSONB,
            raw_response      JSONB,
            submitted_at      TIMESTAMPTZ,
            status_checked_at TIMESTAMPTZ,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_claims_patient_id ON public.claims (patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_claims_provider_id ON public.claims (provider_id)")
    op.execute("ALTER TABLE public.claims ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'claims'
                  AND policyname = 'providers_own_claims'
            ) THEN
                CREATE POLICY "providers_own_claims" ON public.claims
                FOR ALL USING (
                    provider_id = auth.uid()
                    OR public.current_user_role() = 'admin'
                );
            END IF;
        END $$
    """)

    # ── prior_authorizations ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.prior_authorizations (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id       UUID NOT NULL REFERENCES public.patients(id),
            provider_id      UUID NOT NULL REFERENCES public.users(id),
            availity_auth_id TEXT,
            status           VARCHAR(50),
            service_type     TEXT,
            start_date       DATE,
            end_date         DATE,
            auth_data        JSONB,
            raw_response     JSONB,
            submitted_at     TIMESTAMPTZ,
            status_checked_at TIMESTAMPTZ,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_prior_auths_patient_id ON public.prior_authorizations (patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_prior_auths_provider_id ON public.prior_authorizations (provider_id)")
    op.execute("ALTER TABLE public.prior_authorizations ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'prior_authorizations'
                  AND policyname = 'providers_own_prior_authorizations'
            ) THEN
                CREATE POLICY "providers_own_prior_authorizations" ON public.prior_authorizations
                FOR ALL USING (
                    provider_id = auth.uid()
                    OR public.current_user_role() = 'admin'
                );
            END IF;
        END $$
    """)

    # ── remittances ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.remittances (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_id       UUID NOT NULL REFERENCES public.users(id),
            availity_remit_id TEXT UNIQUE,
            check_number      TEXT,
            payer_id          TEXT,
            payment_date      DATE,
            total_payment     NUMERIC(10,2),
            raw_response      JSONB,
            fetched_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_remittances_provider_id ON public.remittances (provider_id)")
    op.execute("ALTER TABLE public.remittances ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'remittances'
                  AND policyname = 'providers_own_remittances'
            ) THEN
                CREATE POLICY "providers_own_remittances" ON public.remittances
                FOR ALL USING (
                    provider_id = auth.uid()
                    OR public.current_user_role() = 'admin'
                );
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.idx_remittances_provider_id")
    op.execute("DROP TABLE IF EXISTS public.remittances")

    op.execute("DROP INDEX IF EXISTS public.idx_prior_auths_provider_id")
    op.execute("DROP INDEX IF EXISTS public.idx_prior_auths_patient_id")
    op.execute("DROP TABLE IF EXISTS public.prior_authorizations")

    op.execute("DROP INDEX IF EXISTS public.idx_claims_provider_id")
    op.execute("DROP INDEX IF EXISTS public.idx_claims_patient_id")
    op.execute("DROP TABLE IF EXISTS public.claims")
