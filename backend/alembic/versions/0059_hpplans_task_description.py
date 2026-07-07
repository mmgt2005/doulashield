"""reformat mco_hpplans task description to use Step N format

Revision ID: 0059
Revises: 0058
Create Date: 2026-07-07
"""
from alembic import op
from sqlalchemy import text

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None

_NEW = (
    "Step 1 — Contact: Contact Health Partners Plans to request a Provider Participation Agreement. "
    "Visit healthpartnersplans.com/providers or call the provider relations line to obtain the current credentialing application packet. "
    "Step 2 — Submit: Submit the completed application along with the provider's CAQH ID and required supporting documents. "
    "Step 3 — Record: Upload the completed application and any signed LOI here. "
    "Record reference number, submission date, and contract date in notes."
)

_OLD = (
    "Contact Health Partners Plans to request a Provider Participation Agreement. "
    "Visit healthpartnersplans.com/providers or call the provider relations line to obtain "
    "the current credentialing application packet. Submit the completed application along "
    "with the provider's CAQH ID and required supporting documents. "
    "Upload the completed application and any signed LOI here. Record reference number, "
    "submission date, and contract date in notes."
)


def upgrade() -> None:
    op.get_bind().execute(
        text("UPDATE public.enrollment_tasks SET description = :desc WHERE task_key = 'mco_hpplans'"),
        {"desc": _NEW},
    )


def downgrade() -> None:
    op.get_bind().execute(
        text("UPDATE public.enrollment_tasks SET description = :desc WHERE task_key = 'mco_hpplans'"),
        {"desc": _OLD},
    )
