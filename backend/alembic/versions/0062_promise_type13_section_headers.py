"""Add ## section header markers to promise_type13 task description

Revision ID: 0062
Revises: 0061
Create Date: 2026-07-23
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None

_NEW_DESCRIPTION = (
    "## INDIVIDUAL PROVIDER (Type 1 NPI)\n"
    "Use the 'Stage & Share' method: build the application first, then screen-share "
    "with the provider for final attestation. The provider must personally check the "
    "boxes, type their legal name, and click Submit — you cannot submit on their behalf. "
    "Confirm their NPI is active in NPPES with taxonomy 374J00000X before starting.\n\n"
    "Step 1 — Portal: Navigate to promise.dhs.pa.gov. Create an account if the "
    "provider is new. Select 'Enroll as a New Provider.'\n"
    "Step 2 — Provider Type: Select Provider Type 13 (Non-Traditional Provider), "
    "Specialty 130 (Certified Doula).\n"
    "Step 3 — Tax ID: Enter the provider's SSN (sole proprietors) or EIN if "
    "incorporated, exactly as it appears on their W-9. Do not mix SSN and EIN.\n"
    "Step 4 — Service Address: Look up the ZIP+4 at usps.com/zip4 before entering — "
    "the 9-digit code ensures the state-assigned Service Location Code (0001) aligns "
    "with future MCO claims.\n"
    "Step 5 — Credentials: Enter the PCB CPD certificate number and exact issuance "
    "date. Upload a PDF scan. The name on the certificate must match the NPI "
    "registration exactly.\n"
    "Step 6 — Legal Name: On the 'Legal Billing Entity' screen, enter the name exactly "
    "as it appears on Line 1 of the provider's W-9.\n"
    "Step 7 — Work History: If the provider has any employment gaps of 30+ days in the "
    "past 5 years, enter a one-sentence explanation in the notes field before advancing "
    "— unexplained gaps trigger a DHS Request for Information.\n"
    "Step 8 — Attestation: Screen-share with the provider. They read the compliance "
    "terms, check the boxes, type their legal name, and click Submit. Copy the ATN "
    "immediately — it is your only tracking token. Processing: 30–60 days.\n\n"
    "## AGENCY / GROUP (Type 2 NPI) — DoulaShield may submit after the authorized "
    "representative has reviewed and confirmed the contents.\n\n"
    "Step 1 — Portal: Navigate to promise.dhs.pa.gov. Select 'Enroll as a New "
    "Provider.'\n"
    "Step 2 — Provider Type: Select Provider Type 89 (Atypical Provider — "
    "Organization), Specialty 130 (Certified Doula).\n"
    "Step 3 — EIN & NPI: Enter the agency's EIN (from IRS SS-4 / CP575) and the "
    "Type 2 group NPI from NPPES.\n"
    "Step 4 — Address: Enter the agency's legal business address. List service "
    "counties where doulas operate.\n"
    "Step 5 — Credentials: List each rostered doula's PCB certificate number and "
    "issuance date. Upload a consolidated PDF of all certificates.\n"
    "Step 6 — Insurance: Enter the agency's group policy carrier, number, and expiry "
    "date. Minimum $1M per occurrence / $3M aggregate.\n"
    "Step 7 — Ownership Disclosure: Complete the disclosure for all owners with 5%+ "
    "ownership and all managing employees.\n"
    "Step 8 — Submit: Confirm with the authorized representative, then submit. Copy "
    "the ATN. Processing: 30–60 days.\n\n"
    "Upload a screenshot of the ATN confirmation page as your document for this task."
)

_OLD_DESCRIPTION = (
    "INDIVIDUAL PROVIDER (Type 1 NPI) — Use the 'Stage & Share' method: build the "
    "application first, then screen-share with the provider for final attestation. "
    "The provider must personally check the boxes, type their legal name, and click "
    "Submit — you cannot submit on their behalf. Confirm their NPI is active in NPPES "
    "with taxonomy 374J00000X before starting.\n\n"
    "Step 1 — Portal: Navigate to promise.dhs.pa.gov. Create an account if the "
    "provider is new. Select 'Enroll as a New Provider.'\n"
    "Step 2 — Provider Type: Select Provider Type 13 (Non-Traditional Provider), "
    "Specialty 130 (Certified Doula).\n"
    "Step 3 — Tax ID: Enter the provider's SSN (sole proprietors) or EIN if "
    "incorporated, exactly as it appears on their W-9. Do not mix SSN and EIN.\n"
    "Step 4 — Service Address: Look up the ZIP+4 at usps.com/zip4 before entering — "
    "the 9-digit code ensures the state-assigned Service Location Code (0001) aligns "
    "with future MCO claims.\n"
    "Step 5 — Credentials: Enter the PCB CPD certificate number and exact issuance "
    "date. Upload a PDF scan. The name on the certificate must match the NPI "
    "registration exactly.\n"
    "Step 6 — Legal Name: On the 'Legal Billing Entity' screen, enter the name exactly "
    "as it appears on Line 1 of the provider's W-9.\n"
    "Step 7 — Work History: If the provider has any employment gaps of 30+ days in the "
    "past 5 years, enter a one-sentence explanation in the notes field before advancing "
    "— unexplained gaps trigger a DHS Request for Information.\n"
    "Step 8 — Attestation: Screen-share with the provider. They read the compliance "
    "terms, check the boxes, type their legal name, and click Submit. Copy the ATN "
    "immediately — it is your only tracking token. Processing: 30–60 days.\n\n"
    "AGENCY / GROUP (Type 2 NPI) — DoulaShield may submit after the authorized "
    "representative has reviewed and confirmed the contents.\n\n"
    "Step 1 — Portal: Navigate to promise.dhs.pa.gov. Select 'Enroll as a New "
    "Provider.'\n"
    "Step 2 — Provider Type: Select Provider Type 89 (Atypical Provider — "
    "Organization), Specialty 130 (Certified Doula).\n"
    "Step 3 — EIN & NPI: Enter the agency's EIN (from IRS SS-4 / CP575) and the "
    "Type 2 group NPI from NPPES.\n"
    "Step 4 — Address: Enter the agency's legal business address. List service "
    "counties where doulas operate.\n"
    "Step 5 — Credentials: List each rostered doula's PCB certificate number and "
    "issuance date. Upload a consolidated PDF of all certificates.\n"
    "Step 6 — Insurance: Enter the agency's group policy carrier, number, and expiry "
    "date. Minimum $1M per occurrence / $3M aggregate.\n"
    "Step 7 — Ownership Disclosure: Complete the disclosure for all owners with 5%+ "
    "ownership and all managing employees.\n"
    "Step 8 — Submit: Confirm with the authorized representative, then submit. Copy "
    "the ATN. Processing: 30–60 days.\n\n"
    "Upload a screenshot of the ATN confirmation page as your document for this task."
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "UPDATE public.enrollment_tasks "
            "SET description = :description "
            "WHERE task_key = 'promise_type13'"
        ),
        {"description": _NEW_DESCRIPTION},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "UPDATE public.enrollment_tasks "
            "SET description = :description "
            "WHERE task_key = 'promise_type13'"
        ),
        {"description": _OLD_DESCRIPTION},
    )
