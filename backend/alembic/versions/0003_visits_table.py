"""Add visits table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

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
    op.execute("CREATE TYPE public.visit_type_enum AS ENUM (%s)" % ", ".join(f"'{v}'" for v in _VALID_TYPES))

    op.create_table(
        "visits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("public.patients.id"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("public.users.id"), nullable=False),
        sa.Column("visit_type", sa.Text, nullable=False),
        sa.Column("visit_date", sa.Date, nullable=True),
        sa.Column("subjective", sa.Text, nullable=True),
        sa.Column("objective", sa.Text, nullable=True),
        sa.Column("assessment", sa.Text, nullable=True),
        sa.Column("plan", sa.Text, nullable=True),
        sa.Column("entry", sa.Text, nullable=True),
        sa.Column("birth_time", sa.Time, nullable=True),
        sa.Column("birth_location", sa.Text, nullable=True),
        sa.Column("birth_notes", sa.Text, nullable=True),
        sa.Column("source_image_path", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("patient_id", "visit_type", name="visits_patient_visit_type_unique"),
        sa.CheckConstraint(
            "visit_type IN (%s)" % ", ".join(f"'{v}'" for v in _VALID_TYPES),
            name="visits_visit_type_check",
        ),
        schema="public",
    )

    op.create_index("idx_visits_patient_id", "visits", ["patient_id"], schema="public")
    op.create_index("idx_visits_provider_id", "visits", ["provider_id"], schema="public")

    op.execute("ALTER TABLE public.visits ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("idx_visits_provider_id", table_name="visits", schema="public")
    op.drop_index("idx_visits_patient_id", table_name="visits", schema="public")
    op.drop_table("visits", schema="public")
    op.execute("DROP TYPE IF EXISTS public.visit_type_enum")
