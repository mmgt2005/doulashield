"""Admin-managed PCB enrollment service API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_db, get_user_agent, require_admin
from app.models.billing_provider import BillingProvider
from app.models.enrollment import EnrollmentDocument, EnrollmentService, EnrollmentTask
from app.models.user import User
from app.schemas.enrollment import (
    CompleteMcoContractingRequest,
    CompleteEnrollmentRequest,
    CompleteNppesRequest,
    CompletePcbRequest,
    EnrollmentDocumentRead,
    EnrollmentServiceCreate,
    EnrollmentServiceDetail,
    EnrollmentServiceRead,
    EnrollmentTaskRead,
    EnrollmentTaskUpdate,
)

router = APIRouter(tags=["enrollment"], prefix="/admin/enrollment")

# ── Task seed definitions ──────────────────────────────────────────────────────

_TASK_SEEDS: dict[str, list[dict]] = {
    "education_training": [
        {
            "task_key": "pcb_application_form",
            "required_pathway": "all",
            "label": "PCB Application Info — Complete in DoulaShield",
            "description": (
                "Fill in your personal information, demographics, and doula type using the form on this page. "
                "When complete, click 'Download Pre-filled Application' to get a printable version of "
                "pages 6–8 ready to submit. You will still need to sign pages 12–13 and have page 14 "
                "notarized before mailing. Download the blank official PCB application from your "
                "enrollment status page."
            ),
            "sort_order": 0,
        },
        {
            "task_key": "pcb_training_hours",
            "required_pathway": "education_training",
            "label": "Training Certificate(s) — 24 Hours Minimum",
            "description": (
                "Upload training program certificate(s) totaling ≥ 24 hours. Each certificate must "
                "explicitly show: (1) your name, (2) training program title, (3) start and end dates, "
                "(4) total hours awarded, and (5) training organization name. "
                "Training sign-in sheets are NOT accepted — only official certificates. "
                "All hours must relate to perinatal doula knowledge areas (birth support, postpartum "
                "care, breastfeeding, perinatal mood disorders, etc.). Upload all certificates if "
                "hours are spread across multiple programs."
            ),
            "sort_order": 1,
        },
        {
            "task_key": "pcb_hipaa_cert",
            "required_pathway": "education_training",
            "label": "HIPAA/Confidentiality Training Certificate — 1 Hour Minimum",
            "description": (
                "Upload a certificate showing ≥ 1 hour of HIPAA or client confidentiality training. "
                "Certificate must show your name, training title, dates, hours, and organization name. "
                "A standalone online HIPAA course is acceptable. If HIPAA is a module within your main "
                "training program, the certificate must list it separately with its own hour count."
            ),
            "sort_order": 2,
        },
        {
            "task_key": "pcb_cpr_cert",
            "required_pathway": "all",
            "label": "CPR Certification — Adult + Infant",
            "description": (
                "Upload a current, unexpired CPR certificate explicitly covering adult AND infant "
                "competencies. Accepted issuers: AHA BLS, American Red Cross CPR/AED for Professional "
                "Rescuers. Online-only certifications without a hands-on skills component are NOT "
                "accepted by PCB."
            ),
            "sort_order": 3,
        },
        {
            "task_key": "pcb_client_eval_1",
            "required_pathway": "all",
            "label": "Client Evaluation #1 (within last year)",
            "description": (
                "Upload two documents as a single PDF: (1) the signed client consent form and "
                "(2) the completed PCB Client Evaluation form. The evaluation must be rated across "
                "9 competencies: communication, active listening, comfort measures, emotional support, "
                "advocacy, information sharing, postpartum support, breastfeeding support, and referrals "
                "to resources — include your comments for each. Must be from a client served within the "
                "last 12 months. If you do not reside in Pennsylvania, the client must be PA-based."
            ),
            "sort_order": 4,
        },
        {
            "task_key": "pcb_client_eval_2",
            "required_pathway": "all",
            "label": "Client Evaluation #2 (within last year)",
            "description": (
                "Upload two documents as a single PDF: (1) the signed client consent form and "
                "(2) the completed PCB Client Evaluation form rated across all 9 competencies with "
                "your comments. Must be from a client served within the last 12 months. "
                "If you do not reside in Pennsylvania, the client must be PA-based."
            ),
            "sort_order": 5,
        },
        {
            "task_key": "pcb_client_eval_3",
            "required_pathway": "all",
            "label": "Client Evaluation #3 (within last year)",
            "description": (
                "Upload two documents as a single PDF: (1) the signed client consent form and "
                "(2) the completed PCB Client Evaluation form rated across all 9 competencies with "
                "your comments. Must be from a client served within the last 12 months. "
                "If you do not reside in Pennsylvania, the client must be PA-based."
            ),
            "sort_order": 6,
        },
        {
            "task_key": "pcb_notarized_ar",
            "required_pathway": "all",
            "label": "Notarized Acknowledgements & Release (Page 14)",
            "description": (
                "Complete page 14 of the PCB application in the presence of a notary public. "
                "The notary must sign, affix their stamp/seal, and date the page. "
                "Electronic or digital notarization is NOT accepted — must be physical. "
                "To find a notary: UPS Store locations, bank branches, and many public libraries "
                "offer free or low-cost notary services. Upload a scan of the completed notarized page."
            ),
            "sort_order": 7,
        },
        {
            "task_key": "pcb_application_submit",
            "required_pathway": "all",
            "label": "Submit Application + Pay $50 Fee",
            "description": (
                "Assemble all completed pages and supporting documents into a single PDF. "
                "Submit by email to info@pacertboard.org (PDF attachments only — no links or cloud drives). "
                "The $50 application fee must accompany your submission; pay by check made payable to "
                "'PCB' or per payment instructions on the application form. "
                "Record your submission date and any confirmation details in the notes field."
            ),
            "sort_order": 8,
        },
    ],
    "experienced": [
        {
            "task_key": "pcb_application_form",
            "required_pathway": "all",
            "label": "PCB Application Info — Complete in DoulaShield",
            "description": (
                "Fill in your personal information, demographics, and doula type using the form on this page. "
                "When complete, click 'Download Pre-filled Application' to get a printable version of "
                "pages 6–8 ready to submit. You will still need to sign pages 12–13 and have page 14 "
                "notarized before mailing. Download the blank official PCB application from your "
                "enrollment status page."
            ),
            "sort_order": 0,
        },
        {
            "task_key": "pcb_experience_current",
            "required_pathway": "experienced",
            "label": "Experience Documentation — Current Position",
            "description": (
                "Upload a letter on company letterhead (or a signed self-statement if self-employed) "
                "confirming your active doula practice. Must include: Agency/Organization Name, City, "
                "State, Zip Code, Your Title, Employment Start Date, Average Hours per Week, and "
                "Estimated Total Hours served to date. If self-employed, include your business address "
                "and approximate client volume."
            ),
            "sort_order": 1,
        },
        {
            "task_key": "pcb_experience_previous",
            "required_pathway": "experienced",
            "label": "Experience Documentation — Previous Position(s) (if needed)",
            "description": (
                "If your current position alone does not demonstrate sufficient doula experience, "
                "upload company letterhead letters for each previous position. Each letter must include: "
                "Agency/Organization Name, City, State, Zip, Your Title, Start Date, End Date, "
                "Hours per Week, and Total Hours in that role. Letters must be signed by a supervisor "
                "or agency director. A resume is NOT a substitute for these letters."
            ),
            "sort_order": 2,
        },
        {
            "task_key": "pcb_cpr_cert",
            "required_pathway": "all",
            "label": "CPR Certification — Adult + Infant",
            "description": (
                "Upload a current, unexpired CPR certificate explicitly covering adult AND infant "
                "competencies. Accepted issuers: AHA BLS, American Red Cross CPR/AED for Professional "
                "Rescuers. Online-only certifications without a hands-on skills component are NOT "
                "accepted by PCB."
            ),
            "sort_order": 3,
        },
        {
            "task_key": "pcb_client_eval_1",
            "required_pathway": "all",
            "label": "Client Evaluation #1 (within last year)",
            "description": (
                "Upload two documents as a single PDF: (1) the signed client consent form and "
                "(2) the completed PCB Client Evaluation form. The evaluation must be rated across "
                "9 competencies: communication, active listening, comfort measures, emotional support, "
                "advocacy, information sharing, postpartum support, breastfeeding support, and referrals "
                "to resources — include your comments for each. Must be from a client served within the "
                "last 12 months. If you do not reside in Pennsylvania, the client must be PA-based."
            ),
            "sort_order": 4,
        },
        {
            "task_key": "pcb_client_eval_2",
            "required_pathway": "all",
            "label": "Client Evaluation #2 (within last year)",
            "description": (
                "Upload two documents as a single PDF: (1) the signed client consent form and "
                "(2) the completed PCB Client Evaluation form rated across all 9 competencies with "
                "your comments. Must be from a client served within the last 12 months. "
                "If you do not reside in Pennsylvania, the client must be PA-based."
            ),
            "sort_order": 5,
        },
        {
            "task_key": "pcb_client_eval_3",
            "required_pathway": "all",
            "label": "Client Evaluation #3 (within last year)",
            "description": (
                "Upload two documents as a single PDF: (1) the signed client consent form and "
                "(2) the completed PCB Client Evaluation form rated across all 9 competencies with "
                "your comments. Must be from a client served within the last 12 months. "
                "If you do not reside in Pennsylvania, the client must be PA-based."
            ),
            "sort_order": 6,
        },
        {
            "task_key": "pcb_ref_letter_1",
            "required_pathway": "experienced",
            "label": "Letter of Recommendation #1 (within last year)",
            "description": (
                "Upload a signed letter of recommendation from a family you served within the last "
                "12 months. Free-form letter — not a PCB form. Must be signed and dated by the client."
            ),
            "sort_order": 7,
        },
        {
            "task_key": "pcb_ref_letter_2",
            "required_pathway": "experienced",
            "label": "Letter of Recommendation #2 (within last year)",
            "description": (
                "Upload a signed letter of recommendation from a family you served within the last "
                "12 months. Free-form letter, signed and dated by the client."
            ),
            "sort_order": 8,
        },
        {
            "task_key": "pcb_ref_letter_3",
            "required_pathway": "experienced",
            "label": "Letter of Recommendation #3 (within last year)",
            "description": (
                "Upload a signed letter of recommendation from a family you served within the last "
                "12 months. Free-form letter, signed and dated by the client."
            ),
            "sort_order": 9,
        },
        {
            "task_key": "pcb_notarized_ar",
            "required_pathway": "all",
            "label": "Notarized Acknowledgements & Release (Page 14)",
            "description": (
                "Complete page 14 of the PCB application in the presence of a notary public. "
                "The notary must sign, affix their stamp/seal, and date the page. "
                "Electronic or digital notarization is NOT accepted — must be physical. "
                "To find a notary: UPS Store locations, bank branches, and many public libraries "
                "offer free or low-cost notary services. Upload a scan of the completed notarized page."
            ),
            "sort_order": 10,
        },
        {
            "task_key": "pcb_application_submit",
            "required_pathway": "all",
            "label": "Submit Application + Pay $50 Fee",
            "description": (
                "Assemble all completed pages and supporting documents into a single PDF. "
                "Submit by email to info@pacertboard.org (PDF attachments only — no links or cloud drives). "
                "The $50 application fee must accompany your submission; pay by check made payable to "
                "'PCB' or per payment instructions on the application form. "
                "Record your submission date and any confirmation details in the notes field."
            ),
            "sort_order": 11,
        },
    ],
}


_STAGE2_TASKS: list[dict] = [
    {
        "task_key": "w9",
        "required_pathway": "all",
        "label": "W-9 Form",
        "description": (
            "Upload a completed, signed IRS Form W-9 for the provider. "
            "The legal name and TIN must match what will be submitted to PROMISe™ and CAQH. "
            "If the provider operates as a sole proprietor, use their SSN; if they have an EIN, use that."
        ),
        "sort_order": 1,
    },
    {
        "task_key": "govt_id",
        "required_pathway": "all",
        "label": "Government-Issued Photo ID",
        "description": (
            "Upload a clear copy of the provider's current, unexpired government-issued photo ID. "
            "Acceptable: driver's license, state ID, or passport. "
            "Both front and back of a driver's license or state ID must be included."
        ),
        "sort_order": 2,
    },
    {
        "task_key": "liability_face_sheet",
        "required_pathway": "all",
        "label": "Liability Insurance Face Sheet",
        "description": (
            "Upload the declarations page (face sheet) from the provider's professional liability "
            "insurance policy. Must show: insured name, policy number, coverage dates, and minimum "
            "limits of $1,000,000 per occurrence / $3,000,000 aggregate. "
            "DoulaShield's group policy covers all enrolled providers — upload that face sheet "
            "once confirmed by the agency."
        ),
        "sort_order": 3,
    },
    {
        "task_key": "promise_type13",
        "required_pathway": "all",
        "label": "PROMISe™ Type 13 Application (Medicaid)",
        "description": (
            "Use the 'Stage & Share' method: build the entire application ahead of time, then bring "
            "the provider in at the end for legal attestation. The provider must personally read the "
            "state compliance terms, check the acknowledgment boxes, type their legal name as their "
            "electronic signature, and click Submit — you cannot legally click Submit on their behalf "
            "for an initial enrollment.\n\n"
            "Prerequisite: Confirm the provider's Type 1 NPI is active in NPPES and carries taxonomy "
            "code 374J00000X (Doula). The PROMISe™ portal cross-checks the federal database in real "
            "time — a missing or mismatched taxonomy will stall progress on screen one.\n\n"
            "Step-by-step:\n"
            "1. Navigate to provider.ipx.pa.gov. If the provider is new to the system, create an "
            "application account. Select 'Enroll as a New Provider' to open a fresh application.\n"
            "2. Select Provider Type 13 (Non-Traditional Provider) from the primary dropdown, then "
            "assign Specialty Code 130 (Certified Doula) directly below it.\n"
            "3. Enter the provider's SSN or EIN exactly as it appears on their IRS documentation. "
            "For the primary service address, look up the exact ZIP+4 code at usps.com/zip4 before "
            "entering it — the 9-digit code ensures the state-assigned 4-digit Service Location Code "
            "(0001) aligns correctly with future MCO claims.\n"
            "4. On the credentials page, enter the PCB Certified Perinatal Doula (CPD) certificate "
            "number and the exact date of issuance. Upload a high-resolution PDF scan of the "
            "certificate. The name on the PCB certificate must match the NPI registration exactly.\n"
            "5. On the 'Legal Billing Entity' screen, enter the name exactly as it appears on Line 1 "
            "of the provider's W-9. A mismatch with the IRS automated match routine forces a manual "
            "review and adds weeks to processing time.\n"
            "6. If the provider has any employment gaps of 30 days or more in the past 5 years, "
            "paste a one-sentence explanation into the system notes field before advancing — "
            "unexplained gaps generate a 'Request for Information' kickback from DHS.\n"
            "7. Advance to the final legal attestation page and bring the provider onto a screen-share "
            "session. Have them read the compliance terms, check the boxes, type their legal name, "
            "and click Submit.\n"
            "8. The moment Submit is clicked, copy the Application Tracking Number (ATN) that appears "
            "on screen into the notes field below. This is your only token for checking status via the "
            "public portal without calling the DHS provider helpline. Processing takes roughly "
            "30–60 days.\n\n"
            "Upload a screenshot of the ATN confirmation page as your document for this task."
        ),
        "sort_order": 4,
    },
    {
        "task_key": "promise_type130",
        "required_pathway": "all",
        "label": "PROMISe™ Type 130 Application (CHIP)",
        "description": (
            "Required to bill CHIP MCOs (Keystone First CHIP, UPMC for You CHIP, etc.). "
            "This is a separate application from Type 13 — complete Type 13 first.\n\n"
            "Follow the same Stage & Share process as Type 13: build the application in advance, "
            "then bring the provider in for live attestation and submit. The provider must personally "
            "sign and submit; you cannot do it on their behalf.\n\n"
            "At provider.ipx.pa.gov, select 'Enroll as a New Provider' again for a fresh application "
            "instance. All classification, demographic, credential, and W-9 name entries follow "
            "the same steps as Type 13 — the only difference is selecting Provider Type 130 (CHIP) "
            "instead of Type 13 in the primary dropdown.\n\n"
            "Record the Type 130 ATN in the notes field below and upload a screenshot of the "
            "ATN confirmation page. Processing also takes 30–60 days."
        ),
        "sort_order": 5,
    },
    {
        "task_key": "caqh_request_access",
        "required_pathway": "all",
        "label": "Request Practice Manager Access in CAQH",
        "description": (
            "Sign in to DoulaShield's CAQH Practice Manager account at proview.caqh.org "
            "(see Admin Guide for one-time agency setup steps — this is a single shared account that "
            "manages all providers). Under the Providers tab, click 'Add Provider' and search by the "
            "provider's NPI. Submit the access request. CAQH will notify the provider by email. "
            "Note: the provider must already have an active CAQH ProView profile; if they are not yet "
            "in the system, they must create an account at proview.caqh.org before you can add them. "
            "Record the request date in the notes field below."
        ),
        "sort_order": 6,
    },
    {
        "task_key": "caqh_provider_authorization",
        "required_pathway": "all",
        "label": "Provider Authorizes DoulaShield in CAQH",
        "description": (
            "The provider must log into their own CAQH ProView account at proview.caqh.org. "
            "Under the 'Authorize' or 'Authorizations' tab, they will see a pending request from "
            "DoulaShield. They must check the box next to DoulaShield and click Authorize. "
            "This step is required before the admin can view or edit the provider's profile in "
            "Practice Manager — without authorization the search returns no results. "
            "The provider cannot delegate this step; they must do it themselves. "
            "Use the 'Start doxy.me Screen-Share' button to schedule a quick call and walk them through it. "
            "Once authorized, the provider's profile becomes accessible in Practice Manager."
        ),
        "sort_order": 7,
    },
    {
        "task_key": "caqh_profile_attested",
        "required_pathway": "all",
        "label": "Complete CAQH Profile & Provider Attests",
        "description": (
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
        "sort_order": 8,
    },
]

_STAGE3_TASKS: list[dict] = [
    {
        "task_key": "mco_work_history",
        "required_pathway": "all",
        "label": "5-Year Work History",
        "description": (
            "Upload a document listing the provider's work history for the past 5 years. "
            "Include: employer/agency name, address, dates of employment, and reason for leaving. "
            "Gaps of 6 months or more must be explained. "
            "This is submitted with each MCO credentialing application."
        ),
        "sort_order": 1,
    },
    {
        "task_key": "mco_resume_cv",
        "required_pathway": "all",
        "label": "Resume / CV",
        "description": (
            "Upload the provider's current resume or curriculum vitae. "
            "Should highlight doula experience, training certifications, and any clinical or "
            "perinatal health-related experience. Several MCOs request this as part of their "
            "credentialing packet."
        ),
        "sort_order": 2,
    },
    {
        "task_key": "mco_amerihealth",
        "required_pathway": "all",
        "label": "AmeriHealth Caritas — Application + LOI",
        "description": (
            "Upload the completed AmeriHealth Caritas PA credentialing application and Letter of "
            "Intent (LOI). The LOI should state the provider's intent to contract as a doula "
            "under the agency's billing NPI. Record the application reference number and submission "
            "date in notes. Record the contract signing date in the Contract Date field when received."
        ),
        "sort_order": 3,
    },
    {
        "task_key": "mco_keystone",
        "required_pathway": "all",
        "label": "Keystone First — Application + LOI",
        "description": (
            "Upload the completed Keystone First credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 4,
    },
    {
        "task_key": "mco_upmc",
        "required_pathway": "all",
        "label": "UPMC For You — Application + LOI",
        "description": (
            "Upload the completed UPMC For You credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 5,
    },
    {
        "task_key": "mco_geisinger",
        "required_pathway": "all",
        "label": "Geisinger Health Plan — Application + LOI",
        "description": (
            "Upload the completed Geisinger Health Plan credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 6,
    },
    {
        "task_key": "mco_highmark",
        "required_pathway": "all",
        "label": "Highmark Wholecare — Application + LOI",
        "description": (
            "Upload the completed Highmark Wholecare credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 7,
    },
    {
        "task_key": "mco_uhc",
        "required_pathway": "all",
        "label": "UnitedHealthcare Community Plan — Application + LOI",
        "description": (
            "Upload the completed UnitedHealthcare Community Plan credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 8,
    },
    {
        "task_key": "mco_aetna",
        "required_pathway": "all",
        "label": "Aetna Better Health — Application + LOI",
        "description": (
            "Upload the completed Aetna Better Health PA credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 9,
    },
    {
        "task_key": "mco_hpplans",
        "required_pathway": "all",
        "label": "Health Partners Plans — Application + LOI",
        "description": (
            "Upload the completed Health Partners Plans credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 10,
    },
]

_NPPES_TASKS: list[dict] = [
    {
        "task_key": "nppes_ia_account",
        "required_pathway": "all",
        "label": "Create I&A System Account",
        "description": (
            "Go to nppes.cms.hhs.gov/IAWeb → click 'Create or Manage an Account'. "
            "Enter the doula's legal name, SSN, date of birth, and primary email, then set up Multi-Factor Authentication (MFA). "
            "RIDP requirement: The system triggers Remote Identity Proofing (RIDP) — timed, automated questions drawn "
            "from the provider's personal credit history (e.g., 'Which bank holds your auto loan?', 'Which of these "
            "is a past address?'). The provider must answer these themselves; DoulaShield cannot complete RIDP on their behalf. "
            "Recommended approach — 10-minute screen-share: Schedule a quick call with the provider. Have them open "
            "the portal and share their screen (or walk them through by phone). They enter their basic info, answer the "
            "RIDP questions, and complete MFA setup. Once they pass RIDP and receive a username, DoulaShield's pending "
            "surrogacy invitation appears immediately on their My Connections dashboard — they can click Approve while "
            "you are still on the call. This activates the link within 24 hours with no paper needed. "
            "If the provider cannot be reached for a screen-share or fails RIDP, proceed to Pathway B after the NPI is issued."
        ),
        "sort_order": 1,
    },
    {
        "task_key": "nppes_application_start",
        "required_pathway": "all",
        "label": "Start NPI Application",
        "description": (
            "Log in to NPPES using the I&A credentials → select 'Submit New NPI Application'. "
            "Choose entity type: Type 1 (Individual) — the doula is an individual healthcare provider. "
            "Type 2 is reserved for Organizational Providers that physically furnish medical services "
            "(hospitals, group practices, clinics). It does not apply to individual doulas, and DoulaShield "
            "as a credentialing firm is not eligible for any NPI."
        ),
        "sort_order": 2,
    },
    {
        "task_key": "nppes_provider_profile",
        "required_pathway": "all",
        "label": "Complete Provider Profile",
        "description": (
            "Enter the doula's exact legal name as it appears on their Social Security card. "
            "Any mismatch causes immediate federal rejection. "
            "Enter date of birth, state of birth, and country of birth. "
            "Answer 'No' to the Sole Proprietor question unless the doula has explicitly established "
            "a registered sole proprietorship with its own EIN."
        ),
        "sort_order": 3,
    },
    {
        "task_key": "nppes_business_addresses",
        "required_pathway": "all",
        "label": "Enter Business Addresses",
        "description": (
            "Two addresses are required (they can be the same). "
            "Business Mailing Address: where administrative mail and checks are sent — P.O. Boxes are allowed. "
            "Practice Location Address: the physical location where services are rendered — "
            "P.O. Boxes are strictly forbidden here. "
            "For doulas who provide in-home services, enter their home office address."
        ),
        "sort_order": 4,
    },
    {
        "task_key": "nppes_taxonomy_code",
        "required_pathway": "all",
        "label": "Assign Taxonomy Code",
        "description": (
            "Click 'Add Taxonomy' and enter the 10-character code 374J00000X (Doula). "
            "Do not enter a State License Number — Pennsylvania does not issue traditional medical "
            "licenses for doulas. PCB certification is used instead for Type 13 provider enrollment."
        ),
        "sort_order": 5,
    },
    {
        "task_key": "nppes_contact_identifiers",
        "required_pathway": "all",
        "label": "Contact Person & Identifiers",
        "description": (
            "Other Identifiers: leave blank for new doulas (this is for legacy Medicaid/Medicare IDs). "
            "Endpoint: leave blank (refers to Health Information Exchange networks). "
            "Contact Person: enter the agency's credentialing manager. "
            "If NPPES finds an error with the SSN or address, they will contact this person to resolve it."
        ),
        "sort_order": 6,
    },
    {
        "task_key": "nppes_attest_submit",
        "required_pathway": "all",
        "label": "Attest and Submit",
        "description": (
            "Read the legal Certification Statement. Check the box to electronically sign the application. "
            "Click Submit. "
            "A clean application without an SSN mismatch is typically approved and the 10-digit NPI "
            "issued via email within 1 to 5 business days — often within hours. "
            "Record the NPI number in the notes field below when it arrives."
        ),
        "sort_order": 7,
    },
    {
        "task_key": "nppes_surrogate_link_request",
        "required_pathway": "all",
        "label": "Link DoulaShield as CMS Surrogate",
        "description": (
            "Log into DoulaShield's CMS I&A account at nppes.cms.hhs.gov/IAWeb. Navigate to the My Connections tab, "
            "click the + icon next to DoulaShield's agency name, and select Add Surrogate. "
            "Search for the provider using their 10-digit Type 1 NPI issued in the previous step. "
            "When the provider's name appears, check both PECOS (for enrollment/revalidation management) "
            "and NPPES (for NPI file management). Enter your email address for a confirmation copy, then click Submit. "
            "The connection will show as Pending until approved. "
            "Note: DoulaShield is classified as a 3rd Party Organization and has no NPI — the system links "
            "DoulaShield's EIN-backed account to the provider's clinical profile. "
            "Proceed to the Pathway B task below — the paper form replaces the provider's electronic approval."
        ),
        "sort_order": 8,
    },
    {
        "task_key": "nppes_surrogate_pathway_a",
        "required_pathway": "all",
        "label": "Pathway A — Electronic Approval (Optional, Fastest)",
        "description": (
            "Pathway A activates the surrogacy link within 24 hours with no paper. "
            "Use this if the provider completed their I&A account setup in the first task (screen-share session). "
            "If they approved the invitation during the screen-share call: mark this task complete — no further action needed. "
            "If they created their account but did not approve yet: ask the provider to log into nppes.cms.hhs.gov/IAWeb. "
            "On their home dashboard under My Connections they will see DoulaShield's pending request. "
            "They click Approve next to both PECOS and NPPES. "
            "Once approved via either route, skip Pathway B and proceed directly to Confirm Surrogacy Active. "
            "If the provider has no I&A account, could not schedule a screen-share, or failed RIDP, "
            "leave this task incomplete and proceed to Pathway B instead."
        ),
        "sort_order": 9,
    },
    {
        "task_key": "nppes_surrogate_pathway_b",
        "required_pathway": "all",
        "label": "Pathway B — Paper Surrogacy Approval Form",
        "description": (
            "Use this only when Pathway A is not possible (provider has no I&A account, failed identity proofing, "
            "or is locked out of CMS portals). "
            "1. Log into DoulaShield's I&A account at nppes.cms.hhs.gov/IAWeb → My Connections tab. "
            "2. Find the provider and click the Tracking ID link for their pending request. "
            "3. Select 'Optional Surrogacy Confirmation' to open and print the form. "
            "4. The provider signs the top box; DoulaShield's Authorized Official signs the second box. "
            "5. Back in I&A, select 'Add a Document', choose the signed file, and select the document type. "
            "6. After the upload completes and you receive the confirmation message, submit the surrogacy request. "
            "An EUS agent will manually link the accounts — allow 5–10 business days. "
            "Upload a scan of the signed form here as your record."
        ),
        "sort_order": 10,
    },
    {
        "task_key": "nppes_surrogate_confirmed",
        "required_pathway": "all",
        "label": "Confirm Surrogacy Active in CMS",
        "description": (
            "Log into DoulaShield's CMS I&A account → My Connections. The provider's entry should now show "
            "status Linked (not Pending). Pathway A links typically activate within 24 hours; "
            "Pathway B paper forms take 5–10 business days. "
            "Once confirmed, DoulaShield staff can manage this provider's NPPES record and submit PECOS "
            "updates on their behalf without the provider logging in. "
            "Record the confirmed date in the notes field below. "
            "If the status still shows Pending after 10 business days, contact EUS at 1-855-267-1515. "
            "Staff delegation: as Authorized Official you can invite your employees as Staff End Users — "
            "they automatically inherit access to all linked providers in PECOS."
        ),
        "sort_order": 11,
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_service_or_404(service_id: uuid.UUID, db: AsyncSession) -> EnrollmentService:
    result = await db.execute(select(EnrollmentService).where(EnrollmentService.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment service not found")
    return service


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/services", response_model=list[EnrollmentServiceRead])
async def list_enrollment_services(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EnrollmentServiceRead]:
    result = await db.execute(
        select(EnrollmentService).order_by(EnrollmentService.created_at.desc())
    )
    services = result.scalars().all()
    return [EnrollmentServiceRead.model_validate(s) for s in services]


@router.post("/services", response_model=EnrollmentServiceDetail, status_code=status.HTTP_201_CREATED)
async def create_enrollment_service(
    body: EnrollmentServiceCreate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceDetail:
    provider_result = await db.execute(select(User).where(User.id == body.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider or provider.role != "provider":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    stage = body.stage or "pcb"

    if stage == "pcb":
        if not body.pcb_pathway:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pcb_pathway is required for PCB enrollment services.",
            )

    if stage == "nppes_setup":
        if not provider.pcb_last_certified_on:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="PCB Certification must be complete before starting NPPES/NPI Setup.",
            )

    if stage == "enrollment":
        if not provider.pcb_last_certified_on:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stage 1 (PCB certification) must be complete before starting Stage 2 enrollment.",
            )
        if not provider.npi:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="NPPES/NPI Setup must be complete (NPI on file) before starting Stage 2 enrollment.",
            )

    if stage == "mco_contracting":
        stage2_result = await db.execute(
            select(EnrollmentService).where(
                EnrollmentService.provider_id == body.provider_id,
                EnrollmentService.stage == "enrollment",
                EnrollmentService.status == "complete",
            )
        )
        if not stage2_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stage 2 (enrollment) must be complete before starting MCO contracting.",
            )

    service = EnrollmentService(
        provider_id=body.provider_id,
        created_by=current_user.id,
        stage=stage,
        pcb_pathway=body.pcb_pathway if stage == "pcb" else None,
        status="in_progress",
        intake_data=body.intake_data,
    )
    db.add(service)
    await db.flush()

    if stage == "pcb":
        task_seeds = _TASK_SEEDS.get(body.pcb_pathway, [])
    elif stage == "nppes_setup":
        task_seeds = _NPPES_TASKS
    elif stage == "enrollment":
        task_seeds = _STAGE2_TASKS
    else:
        task_seeds = _STAGE3_TASKS

    tasks: list[EnrollmentTask] = []
    for seed in task_seeds:
        task = EnrollmentTask(
            service_id=service.id,
            task_key=seed["task_key"],
            required_pathway=seed["required_pathway"],
            label=seed["label"],
            description=seed["description"],
            sort_order=seed["sort_order"],
            status="not_started",
        )
        db.add(task)
        tasks.append(task)

    await db.commit()
    await db.refresh(service)
    for t in tasks:
        await db.refresh(t)

    await audit.log(
        action="ENROLLMENT_SERVICE_CREATED",
        user_id=current_user.id,
        resource_type="user",
        resource_id=body.provider_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "service_id": str(service.id),
            "stage": stage,
            "pathway": body.pcb_pathway,
        },
    )

    return EnrollmentServiceDetail(
        service=EnrollmentServiceRead.model_validate(service),
        tasks=[EnrollmentTaskRead.model_validate(t) for t in tasks],
        documents=[],
        provider_email=provider.email,
        provider_name=provider.full_name,
    )


@router.get("/services/{service_id}", response_model=EnrollmentServiceDetail)
async def get_enrollment_service(
    service_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnrollmentServiceDetail:
    service = await _get_service_or_404(service_id, db)

    tasks_result = await db.execute(
        select(EnrollmentTask)
        .where(EnrollmentTask.service_id == service_id)
        .order_by(EnrollmentTask.sort_order)
    )
    tasks = tasks_result.scalars().all()

    docs_result = await db.execute(
        select(EnrollmentDocument)
        .where(EnrollmentDocument.service_id == service_id)
        .order_by(EnrollmentDocument.created_at)
    )
    docs = docs_result.scalars().all()

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()

    return EnrollmentServiceDetail(
        service=EnrollmentServiceRead.model_validate(service),
        tasks=[EnrollmentTaskRead.model_validate(t) for t in tasks],
        documents=[EnrollmentDocumentRead.model_validate(d) for d in docs],
        provider_email=provider.email if provider else None,
        provider_name=provider.full_name if provider else None,
    )


@router.patch("/tasks/{task_id}", response_model=EnrollmentTaskRead)
async def update_enrollment_task(
    task_id: uuid.UUID,
    body: EnrollmentTaskUpdate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnrollmentTaskRead:
    result = await db.execute(select(EnrollmentTask).where(EnrollmentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Training hours validation
    if body.status == "complete" and task.task_key == "pcb_training_hours":
        hours = (body.task_data or {}).get("hours") or (task.task_data or {}).get("hours", 0)
        if int(hours) < 24:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Training hours must be ≥ 24 to complete this task (currently {hours}).",
            )
    if body.status == "complete" and task.task_key == "pcb_hipaa_cert":
        hours = (body.task_data or {}).get("hours") or (task.task_data or {}).get("hours", 0)
        if int(hours) < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="HIPAA training hours must be ≥ 1 to complete this task.",
            )

    if body.status is not None:
        task.status = body.status
        if body.status == "complete":
            task.completed_at = datetime.now(timezone.utc)
        elif task.completed_at is not None:
            task.completed_at = None
    if body.notes is not None:
        task.notes = body.notes
    if body.task_data is not None:
        task.task_data = body.task_data

    await db.commit()
    await db.refresh(task)
    return EnrollmentTaskRead.model_validate(task)


class _ScreenshareInviteRequest(BaseModel):
    doxy_me_url: str


@router.post("/tasks/{task_id}/screenshare-invite")
async def send_screenshare_invite(
    task_id: uuid.UUID,
    body: _ScreenshareInviteRequest,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from app.services import email_service
    result = await db.execute(select(EnrollmentTask).where(EnrollmentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    svc_result = await db.execute(select(EnrollmentService).where(EnrollmentService.id == task.service_id))
    service = svc_result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider or not provider.email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if task.task_key == "caqh_provider_authorization":
        await email_service.send_caqh_screenshare_invite(
            to_email=provider.email,
            provider_name=provider.full_name or provider.email,
            doxy_me_url=body.doxy_me_url,
        )
    else:
        await email_service.send_screenshare_invite(
            to_email=provider.email,
            provider_name=provider.full_name or provider.email,
            doxy_me_url=body.doxy_me_url,
        )
    return {"sent": True, "to": provider.email}


@router.post("/services/{service_id}/complete-pcb", response_model=EnrollmentServiceRead)
async def complete_pcb_certification(
    service_id: uuid.UUID,
    body: CompletePcbRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    service = await _get_service_or_404(service_id, db)

    service.status = "complete"
    service.pcb_cert_date = body.cert_date

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()
    if provider:
        provider.pcb_last_certified_on = body.cert_date

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="PCB_CERTIFICATION_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=service.provider_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "service_id": str(service_id),
            "cert_date": str(body.cert_date),
        },
    )

    return EnrollmentServiceRead.model_validate(service)


@router.post("/services/{service_id}/complete-nppes", response_model=EnrollmentServiceRead)
async def complete_nppes_setup(
    service_id: uuid.UUID,
    body: CompleteNppesRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    service = await _get_service_or_404(service_id, db)
    if service.stage != "nppes_setup":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint is only for NPPES/NPI Setup services.",
        )

    npi = body.npi.strip()
    if not npi.isdigit() or len(npi) != 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="NPI must be exactly 10 digits.",
        )

    service.status = "complete"
    intake = dict(service.intake_data or {})
    intake["npi"] = npi
    service.intake_data = intake

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()
    if provider:
        provider.npi = npi

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="NPPES_SETUP_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=service.provider_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "service_id": str(service_id),
            "npi": npi,
        },
    )

    return EnrollmentServiceRead.model_validate(service)


@router.post("/services/{service_id}/complete-enrollment", response_model=EnrollmentServiceRead)
async def complete_enrollment(
    service_id: uuid.UUID,
    body: CompleteEnrollmentRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    service = await _get_service_or_404(service_id, db)
    if service.stage != "enrollment":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint is only for Stage 2 enrollment services.",
        )

    service.status = "complete"
    intake = dict(service.intake_data or {})
    if body.promise_id:
        intake["promise_id"] = body.promise_id
    if body.caqh_id:
        intake["caqh_id"] = body.caqh_id
    service.intake_data = intake

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()
    if provider:
        provider.promise_last_enrolled_on = body.promise_enrolled_on
        if body.liability_insurance_expires_on:
            provider.liability_insurance_expires_on = body.liability_insurance_expires_on

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="ENROLLMENT_STAGE2_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=service.provider_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "service_id": str(service_id),
            "promise_enrolled_on": str(body.promise_enrolled_on),
        },
    )

    return EnrollmentServiceRead.model_validate(service)


@router.post("/services/{service_id}/complete-mco-contracting", response_model=EnrollmentServiceRead)
async def complete_mco_contracting(
    service_id: uuid.UUID,
    body: CompleteMcoContractingRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    service = await _get_service_or_404(service_id, db)
    if service.stage != "mco_contracting":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint is only for Stage 3 MCO contracting services.",
        )

    service.status = "complete"
    intake = dict(service.intake_data or {})
    intake["contracted_on"] = str(body.contracted_on)
    service.intake_data = intake

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="ENROLLMENT_STAGE3_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=service.provider_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "service_id": str(service_id),
            "contracted_on": str(body.contracted_on),
        },
    )

    return EnrollmentServiceRead.model_validate(service)


@router.post(
    "/services/{service_id}/tasks/{task_id}/documents",
    response_model=EnrollmentDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_enrollment_document(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_type: Annotated[str, Form()] = "other",
) -> EnrollmentDocumentRead:
    from app.services.ocr_service import store_image

    _MAX_BYTES = 20 * 1024 * 1024
    _ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, or PDF files are accepted.",
        )

    content_bytes = await file.read()
    if len(content_bytes) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File must be under 20 MB.",
        )

    service = await _get_service_or_404(service_id, db)

    task_result = await db.execute(
        select(EnrollmentTask).where(
            EnrollmentTask.id == task_id,
            EnrollmentTask.service_id == service_id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    file_path = await store_image(
        content_bytes, content_type, None, current_user.id, f"enrollment-doc-{service_id}"
    )

    doc = EnrollmentDocument(
        service_id=service_id,
        task_id=task_id,
        uploaded_by=current_user.id,
        file_path=file_path,
        file_name=file.filename or "document",
        document_type=document_type,
    )
    db.add(doc)

    if task.status == "not_started":
        task.status = "in_progress"

    await db.commit()
    await db.refresh(doc)
    return EnrollmentDocumentRead.model_validate(doc)


@router.get("/services/{service_id}/documents/{doc_id}/url")
async def get_enrollment_document_url(
    service_id: uuid.UUID,
    doc_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from app.services.ocr_service import get_signed_url

    doc_result = await db.execute(
        select(EnrollmentDocument).where(
            EnrollmentDocument.id == doc_id,
            EnrollmentDocument.service_id == service_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    url = await get_signed_url(doc.file_path, expires_in=300)
    return {"url": url, "file_name": doc.file_name}


@router.post("/services/{service_id}/assign-to-billing-admin", response_model=EnrollmentServiceRead)
async def assign_enrollment_to_billing_admin(
    service_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    """Toggle assignment of an enrollment service to the provider's billing admin agency.

    Assigning lets the billing admin see and manage this service from their My Providers
    panel without creating a duplicate. Toggling again removes the assignment flag.
    """
    service = await _get_service_or_404(service_id, db)

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider or not provider.billing_provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider is not assigned to a billing agency. Assign the provider to an agency first.",
        )

    service.assigned_to_billing_admin = not service.assigned_to_billing_admin

    tier_newly_enabled = False
    if service.assigned_to_billing_admin:
        # Auto-enable the enrollment tier so the billing admin can immediately
        # see and manage this service from My Providers without a separate step.
        bp_result = await db.execute(
            select(BillingProvider).where(BillingProvider.id == provider.billing_provider_id)
        )
        bp = bp_result.scalar_one_or_none()
        if bp and not bp.enrollment_tier_enabled:
            bp.enrollment_tier_enabled = True
            tier_newly_enabled = True

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="ENROLLMENT_SERVICE_ASSIGNED_TO_BILLING_ADMIN" if service.assigned_to_billing_admin else "ENROLLMENT_SERVICE_UNASSIGNED_FROM_BILLING_ADMIN",
        user_id=current_user.id,
        resource_type="enrollment_service",
        resource_id=service_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "provider_id": str(service.provider_id),
            "billing_provider_id": str(provider.billing_provider_id),
            "assigned": service.assigned_to_billing_admin,
            "enrollment_tier_newly_enabled": tier_newly_enabled,
        },
    )

    return EnrollmentServiceRead.model_validate(service)
