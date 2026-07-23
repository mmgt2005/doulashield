"""Update PROMISe and CAQH task descriptions to step-formatted layout

Revision ID: 0061
Revises: 0060
Create Date: 2026-07-23
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None

_UPDATES = [
    {
        "task_key": "promise_type13",
        "description": (
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
        ),
    },
    {
        "task_key": "caqh_request_access",
        "description": (
            "Step 1 — Sign In: Log in to DoulaShield's shared CAQH Practice Manager account at "
            "proview.caqh.org. See Admin Guide for one-time agency setup — this is a single shared "
            "account that manages all providers.\n"
            "Step 2 — Add Provider: Under the Providers tab, click 'Add Provider' and search by "
            "the provider's NPI. Submit the access request — CAQH will notify the provider by email.\n"
            "Step 3 — Prerequisite Check: The provider must already have an active CAQH ProView "
            "profile. If they are not yet in the system, they must create an account at "
            "proview.caqh.org before you can add them.\n"
            "Step 4 — Record: Note the request date in the notes field below."
        ),
    },
    {
        "task_key": "caqh_provider_authorization",
        "description": (
            "Step 1 — Provider Logs In: The provider logs into their own CAQH ProView account at "
            "proview.caqh.org. This step cannot be delegated — the provider must do it themselves.\n"
            "Step 2 — Authorize DoulaShield: Under the 'Authorize' or 'Authorizations' tab, the "
            "provider will see a pending request from DoulaShield. They check the box next to "
            "DoulaShield and click Authorize.\n"
            "Step 3 — Why It Matters: Without this authorization the admin search returns no results "
            "— the provider's profile is not accessible in Practice Manager until they authorize.\n"
            "Step 4 — Screen-Share If Needed: Use the 'Start doxy.me Screen-Share' button to walk "
            "the provider through the authorization steps if they need assistance."
        ),
    },
    {
        "task_key": "caqh_profile_attested",
        "description": (
            "Step 1 — Open Profile: Log in to CAQH Practice Manager and select the provider.\n"
            "Step 2 — Fill 12 Sections: Complete all sections — Personal Info, Address, Education, "
            "Postgraduate Training, Work History, Hospital Affiliations, Malpractice Insurance, "
            "Liability Insurance, References, Board Certifications, DEA/CDS, and Disclosure "
            "Questions. Your edits save as 'Suggested Import' and are NOT live until the provider attests.\n"
            "Step 3 — Provider Attests: The provider logs into their own CAQH ProView account and "
            "clicks 'Attest' to certify the data. All MCOs require an active, attested profile before "
            "processing credentialing. Attestation expires every 120 days — CAQH emails a reminder "
            "before expiry; notify the provider to re-attest when the cycle approaches.\n"
            "Step 4 — Record & Upload: Note the CAQH ProView ID and attestation date in the notes "
            "field. Upload a screenshot of the 'Attestation Complete' confirmation."
        ),
    },
]

_OLD_DESCRIPTIONS = {
    "promise_type13": (
        "Navigate to promise.dhs.pa.gov and log in with the DoulaShield PROMISe™ account. "
        "Select 'Enroll as a New Provider' and choose Provider Type 13 (Non-Traditional Provider), "
        "Specialty 130 (Certified Doula). Enter the provider's NPI (taxonomy 374J00000X), SSN or EIN, "
        "and service address. Upload the PCB certificate and complete all required sections. "
        "The provider must personally read the attestation, check the compliance boxes, type their "
        "legal name, and click Submit — you cannot do this on their behalf. "
        "Once submitted, copy the Application Tracking Number (ATN) immediately. "
        "Upload a screenshot of the ATN confirmation page. Processing takes 30–60 days."
    ),
    "caqh_request_access": (
        "Sign in to DoulaShield's CAQH Practice Manager account at proview.caqh.org "
        "(see Admin Guide for one-time agency setup steps — this is a single shared account that "
        "manages all providers). Under the Providers tab, click 'Add Provider' and search by the "
        "provider's NPI. Submit the access request. CAQH will notify the provider by email. "
        "Note: the provider must already have an active CAQH ProView profile; if they are not yet "
        "in the system, they must create an account at proview.caqh.org before you can add them. "
        "Record the request date in the notes field below."
    ),
    "caqh_provider_authorization": (
        "The provider must log into their own CAQH ProView account at proview.caqh.org. "
        "Under the 'Authorize' or 'Authorizations' tab, they will see a pending request from "
        "DoulaShield. They must check the box next to DoulaShield and click Authorize. "
        "This step is required before the admin can view or edit the provider's profile in "
        "Practice Manager — without authorization the search returns no results. "
        "The provider cannot delegate this step; they must do it themselves. "
        "Use the 'Start doxy.me Screen-Share' button to schedule a quick call and walk them through it. "
        "Once authorized, the provider's profile becomes accessible in Practice Manager."
    ),
    "caqh_profile_attested": (
        "Once the provider has authorized access, log into CAQH Practice Manager and select the "
        "provider. Fill in all 12 sections of their CAQH ProView profile: Personal Info, Address, "
        "Education, Postgraduate Training, Work History, Hospital Affiliations, Malpractice "
        "Insurance, Liability Insurance, References, Board Certifications, DEA/CDS, and Disclosure "
        "Questions. Your edits are saved as 'Suggested Import' — they are NOT live until the "
        "provider attests. The provider must log into their own CAQH ProView account and click "
        "'Attest' to legally certify the data. "
        "Attestation expires every 120 days; CAQH will email the provider a reminder before expiry. "
        "Record the provider's CAQH ID and the attestation date in the notes field below. "
        "Upload a screenshot of the 'Attestation Complete' confirmation. "
        "All MCOs require an active, attested CAQH ProView profile before processing credentialing. "
        "When the 120-day renewal cycle approaches, notify the provider to re-attest."
    ),
}


def upgrade() -> None:
    conn = op.get_bind()
    for row in _UPDATES:
        conn.execute(
            text(
                "UPDATE public.enrollment_tasks "
                "SET description = :description "
                "WHERE task_key = :task_key"
            ),
            {"description": row["description"], "task_key": row["task_key"]},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for task_key, description in _OLD_DESCRIPTIONS.items():
        conn.execute(
            text(
                "UPDATE public.enrollment_tasks "
                "SET description = :description "
                "WHERE task_key = :task_key"
            ),
            {"description": description, "task_key": task_key},
        )
