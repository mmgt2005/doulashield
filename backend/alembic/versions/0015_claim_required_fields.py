"""Add gender to patients and expand visit_type check constraint

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column("gender", sa.String(1), server_default="F", nullable=False),
        schema="public",
    )

    # Expand visit_type check constraint to include crisis_loss_1 and crisis_loss_2
    op.drop_constraint("visits_visit_type_check", "visits", schema="public", type_="check")
    op.create_check_constraint(
        "visits_visit_type_check",
        "visits",
        "visit_type IN ("
        "'prenatal_1','prenatal_2','prenatal_3','prenatal_4','prenatal_5','prenatal_6',"
        "'labor',"
        "'postnatal_1','postnatal_2','postnatal_3','postnatal_4','postnatal_5','postnatal_6',"
        "'crisis_loss_1','crisis_loss_2'"
        ")",
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint("visits_visit_type_check", "visits", schema="public", type_="check")
    op.create_check_constraint(
        "visits_visit_type_check",
        "visits",
        "visit_type IN ("
        "'prenatal_1','prenatal_2','prenatal_3','prenatal_4','prenatal_5','prenatal_6',"
        "'labor',"
        "'postnatal_1','postnatal_2','postnatal_3','postnatal_4','postnatal_5','postnatal_6'"
        ")",
        schema="public",
    )
    op.drop_column("patients", "gender", schema="public")
