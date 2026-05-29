"""Add visits table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-28
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_VALID_TYPES = (
    "prenatal_1", "prenatal_2", "prenatal_3", "prenatal_4", "prenatal_5", "prenatal_6",
    "labor",
    "postnatal_1", "postnatal_2", "postnatal_3", "postnatal_4", "postnatal_5", "postnatal_6",
)


def upgrade() -> None:
    valid_list = ", ".join(f"'{v}'" for v in _VALID_TYPES)

    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE t.typname = 'visit_type_enum' AND n.nspname = 'public'
            ) THEN
                CREATE TYPE public.visit_type_enum AS ENUM ({valid_list});
            END IF;
        END $$
    """)

    op.execute(f"""
        CREATE TABLE IF NOT EXISTS public.visits (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            patient_id      UUID NOT NULL REFERENCES public.patients(id),
            provider_id     UUID NOT NULL REFERENCES public.users(id),
            visit_type      TEXT NOT NULL,
            visit_date      DATE,
            subjective      TEXT,
            objective       TEXT,
            assessment      TEXT,
            plan            TEXT,
            entry           TEXT,
            birth_time      TIME,
            birth_location  TEXT,
            birth_notes     TEXT,
            source_image_path TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT visits_patient_visit_type_unique UNIQUE (patient_id, visit_type),
            CONSTRAINT visits_visit_type_check CHECK (visit_type IN ({valid_list}))
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_visits_patient_id ON public.visits (patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_visits_provider_id ON public.visits (provider_id)")
    op.execute("ALTER TABLE public.visits ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.idx_visits_provider_id")
    op.execute("DROP INDEX IF EXISTS public.idx_visits_patient_id")
    op.execute("DROP TABLE IF EXISTS public.visits")
    op.execute("DROP TYPE IF EXISTS public.visit_type_enum")
