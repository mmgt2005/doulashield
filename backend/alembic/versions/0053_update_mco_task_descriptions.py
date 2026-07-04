"""Update MCO contracting task labels and descriptions with step-by-step enrollment instructions

Revision ID: 0053
Revises: 0052
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None

_UPDATES = [
    {
        "task_key": "mco_amerihealth",
        "label": "AmeriHealth Caritas — Application + LOI",
        "description": (
            "Step 1 — Contracting: Email the completed Contract Application to "
            "pnmcontracting@amerihealthcaritas.com. "
            "Step 2 — Credentialing: Once AmeriHealth emails back the contract, submit the provider's "
            "CAQH ID and the Application Checklist to the credentialing email or fax provided in the "
            "welcome packet. "
            "Step 3 — Validation: Monitor for a 'Participating ID Number' notice — do not schedule "
            "members under this MCO until that notice arrives. "
            "Upload the completed application and any signed LOI here. Record the application "
            "reference number and submission date in notes. Record the contract signing date when received."
        ),
    },
    {
        "task_key": "mco_keystone",
        "label": "Keystone First — Application + LOI",
        "description": (
            "Step 1 — Contracting: Email the completed Contract Application to "
            "provider.contracting@keystonefirstpa.com. "
            "Step 2 — Credentialing: Once Keystone First emails back the contract, submit the "
            "provider's CAQH ID and the Application Checklist to the credentialing contact provided "
            "in the welcome packet. "
            "Step 3 — Validation: Monitor for a 'Participating ID Number' notice — do not schedule "
            "members under this MCO until that notice arrives. "
            "Upload the completed application and any signed LOI here. Record reference number, "
            "submission date, and contract date in notes."
        ),
    },
    {
        "task_key": "mco_upmc",
        "label": "UPMC For You — Application + LOI",
        "description": (
            "Step 1 — Request: Go to upmchealthplan.com/providers/medical/join-us and select "
            "'Ancillary' to begin the network participation request. "
            "Step 2 — Portal: Enter the provider's CAQH ID when prompted. "
            "Step 3 — Onboarding: If approved, UPMC will send an invitation to the Provider "
            "Onboarding Express portal to upload UPMC-specific assessment forms and professional "
            "documents. Complete all requested uploads promptly. "
            "Upload the completed application and any signed LOI here. Record reference number, "
            "submission date, and contract date in notes."
        ),
    },
    {
        "task_key": "mco_geisinger",
        "label": "Geisinger Health Plan — Application + LOI",
        "description": (
            "Step 1 — Interest Form: Complete the Provider Interest Form at "
            "geisinger.org/health-plan/providers/join-our-network. "
            "Step 2 — CAQH Authorization: Log into the provider's CAQH ProView account and "
            "specifically authorize 'Geisinger Health Plan' to view their data — Geisinger will "
            "not be able to pull credentials without this authorization. "
            "Step 3 — Network Review: Geisinger performs a Network Adequacy review. If approved, "
            "the provider receives a formal Letter of Intent (LOI). "
            "Step 4 — Availity Integration: Upon signing the LOI, the provider will be invited to "
            "link their practice to the Availity Essentials portal. "
            "Upload the completed application and signed LOI here. Record reference number, "
            "submission date, and contract date in notes."
        ),
    },
    {
        "task_key": "mco_highmark",
        "label": "Highmark Wholecare — Application + LOI",
        "description": (
            "Step 1 — Credentialing Request: Complete the Initial Credentialing Request Form at "
            "the Highmark Wholecare provider credentialing portal. "
            "Step 2 — Follow-up: Highmark will email if additional documentation is needed. "
            "Check spam daily — failure to respond will result in application discontinuation. "
            "Step 3 — Contract: After credentialing approval, use the Participating Provider form "
            "at the Highmark Wholecare provider contracting portal to generate the contract. "
            "Upload the completed credentialing request and signed contract here. Record reference "
            "number, submission date, and contract signing date in notes."
        ),
    },
    {
        "task_key": "mco_uhc",
        "label": "UnitedHealthcare Community Plan — Application + LOI",
        "description": (
            "Step 1 — Onboard Pro: Sign in to onboard-pro.uhcprovider.com/Contracting. "
            "Step 2 — Guided Workflow: Enter the provider's Tax ID and state — the portal wizard "
            "will guide document submission. "
            "Step 3 — Tracking: Use the portal dashboard to track real-time application status. "
            "Use the 24/7 portal chat feature for questions. "
            "Upload the completed application and any signed LOI here. Record reference number, "
            "submission date, and contract date in notes."
        ),
    },
    {
        "task_key": "mco_aetna",
        "label": "Aetna Better Health — Application + LOI",
        "description": (
            "Step 1 — Application: Complete the Prospective Provider Online Form at "
            "extaz-oci.aetna.com/pocui/join-the-aetna-network. "
            "Step 2 — Evaluation: Aetna will notify the provider within 45 days if they are "
            "eligible for network participation. "
            "Step 3 — Credentialing: If selected, Aetna pulls data directly from CAQH. "
            "Ensure the provider has logged into their CAQH ProView account and designated "
            "'Aetna Better Health' as an Authorized Health Plan before this step. "
            "Upload the completed application and any signed LOI here. Record reference number, "
            "submission date, and contract date in notes."
        ),
    },
    {
        "task_key": "mco_hpplans",
        "label": "Health Partners Plans — Application + LOI",
        "description": (
            "Contact Health Partners Plans to request a Provider Participation Agreement. "
            "Visit healthpartnersplans.com/providers or call the provider relations line to obtain "
            "the current credentialing application packet. Submit the completed application along "
            "with the provider's CAQH ID and required supporting documents. "
            "Upload the completed application and any signed LOI here. Record reference number, "
            "submission date, and contract date in notes."
        ),
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    for row in _UPDATES:
        conn.execute(
            text(
                "UPDATE public.enrollment_tasks "
                "SET label = :label, description = :description "
                "WHERE task_key = :task_key"
            ),
            {"label": row["label"], "description": row["description"], "task_key": row["task_key"]},
        )


def downgrade() -> None:
    conn = op.get_bind()
    old_descriptions = {
        "mco_amerihealth": (
            "AmeriHealth Caritas — Application + LOI",
            "Upload the completed AmeriHealth Caritas PA credentialing application and Letter of "
            "Intent (LOI). The LOI should state the provider's intent to contract as a doula "
            "under the agency's billing NPI. Record the application reference number and submission "
            "date in notes. Record the contract signing date in the Contract Date field when received.",
        ),
        "mco_keystone": (
            "Keystone First — Application + LOI",
            "Upload the completed Keystone First credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data.",
        ),
        "mco_upmc": (
            "UPMC For You — Application + LOI",
            "Upload the completed UPMC For You credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data.",
        ),
        "mco_geisinger": (
            "Geisinger Health Plan — Application + LOI",
            "Upload the completed Geisinger Health Plan credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data.",
        ),
        "mco_highmark": (
            "Highmark Wholecare — Application + LOI",
            "Upload the completed Highmark Wholecare credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data.",
        ),
        "mco_uhc": (
            "UnitedHealthcare Community Plan — Application + LOI",
            "Upload the completed UnitedHealthcare Community Plan credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data.",
        ),
        "mco_aetna": (
            "Aetna Better Health — Application + LOI",
            "Upload the completed Aetna Better Health PA credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data.",
        ),
        "mco_hpplans": (
            "Health Partners Plans — Application + LOI",
            "Upload the completed Health Partners Plans credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data.",
        ),
    }
    for task_key, (label, description) in old_descriptions.items():
        conn.execute(
            text(
                "UPDATE public.enrollment_tasks "
                "SET label = :label, description = :description "
                "WHERE task_key = :task_key"
            ),
            {"label": label, "description": description, "task_key": task_key},
        )
