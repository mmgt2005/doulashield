# DoulaShield Enrollment Admin Guide

**v1.33.0 · Last updated 2026-06-26**

This guide covers the PCB (Pennsylvania Certification Board) credentialing workflow for admins managing the end-to-end enrollment service. As an enrollment admin, you create enrollment services on behalf of doula providers, collect and verify the required documents, and record outcomes back to the provider's profile.

---

## Table of Contents

1. [How the Enrollment Service Works](#how-the-enrollment-service-works)
2. [Choosing the Right PCB Pathway](#choosing-the-right-pcb-pathway)
3. [Starting an Enrollment Service](#starting-an-enrollment-service)
4. [Task-by-Task Guide: Education/Training Pathway](#task-by-task-guide-educationtraining-pathway)
5. [Task-by-Task Guide: Experienced Pathway](#task-by-task-guide-experienced-pathway)
6. [Submitting to PCB](#submitting-to-pcb)
7. [Recording the PCB Certificate](#recording-the-pcb-certificate)
8. [Reference: Task Completion Checklist](#reference-task-completion-checklist)

---

## How the Enrollment Service Works

When you create an enrollment service for a provider, DoulaShield automatically generates the correct task checklist based on the pathway you select. You work through each task — uploading documents and marking tasks complete — until all required items are in place. Then you submit the application to PCB at pacertboard.org/doula and record the certificate when it arrives.

```
Select pathway
      ↓
Checklist generated automatically
      ↓
Collect + upload documents for each task
      ↓
Mark tasks complete (DoulaShield validates hours)
      ↓
Submit application to PCB (pacertboard.org/doula)
      ↓
Record certificate date in DoulaShield
      ↓
Provider's pcb_last_certified_on updated → Stage 2 (PROMISe, CAQH) unlocked
```

PCB does not have an API — all submissions go through their online application form or by mail.

---

## Choosing the Right PCB Pathway

| If the provider… | Use this pathway |
|---|---|
| Completed a formal doula training program | Education/Training |
| Is already working as a doula (active clients) | Experienced |
| Unsure — default to | Education/Training |

The Education/Training pathway is available to ALL applicants regardless of experience. When in doubt, choose it. The Experienced pathway requires proof of active practice, client evaluations within the last year, AND three letters of recommendation — all three, all from the past year.

---

## Starting an Enrollment Service

1. In the sidebar, click **Admin → Enrollment Services**.
2. Click **+ New Enrollment Service**.
3. Select the provider from the dropdown.
4. Choose the PCB pathway: **Education/Training** or **Experienced**.
5. Click **Create Service** — DoulaShield generates the task checklist automatically.

The pathway can be changed until the first task is marked complete.

---

## Task-by-Task Guide: Education/Training Pathway

### Task 1: Training Certificate(s) — 24 Hours Minimum

**What to collect from the provider:**
A certificate of completion from their doula training program. Acceptable programs include DONA International, CAPPA, ProDoula, Birthing From Within, or any recognized perinatal doula training program. The certificate must show the number of training hours.

**What to verify before uploading:**
- Total hours documented across all certificates must be at least 24
- All 24 hours must relate to perinatal doula knowledge areas (birth support, postpartum care, breastfeeding support, perinatal mood disorders, etc.)
- General topics like "customer service" or unrelated healthcare training do not count toward the 24

**How to enter in DoulaShield:**
Upload the certificate PDF or image. In the **Total training hours** field, enter the cumulative hours from all uploaded certificates. DoulaShield will prevent task completion if the total is under 24.

**If the provider cannot provide a certificate:**
Contact their training program directly — most programs issue replacement certificates for a small fee. PCB does not accept a self-reported hour count without documentation.

---

### Task 2: HIPAA/Confidentiality Training Certificate — 1 Hour Minimum

**What to collect from the provider:**
A certificate showing completion of a HIPAA or client confidentiality course. This can be:
- A standalone online HIPAA training (HIPAATraining.com, Compliancy Group — free options available)
- A confidentiality module within their doula training program **if** the program explicitly lists HIPAA or client confidentiality as a topic with separate hours

**What to verify before uploading:**
- Certificate explicitly mentions HIPAA, health information privacy, or client confidentiality
- At least 1 hour documented
- Certificate is dated (any date is acceptable — PCB does not specify recency for this item)

**If this is part of the same training program certificate:**
If the training certificate lists HIPAA as a distinct topic with hour tracking, you can upload the same file for both Task 1 and Task 2. Enter the HIPAA-specific hours separately in the HIPAA hours field.

---

### Task 3: CPR Certification — Adult + Infant

**What to collect from the provider:**
A valid, unexpired CPR certification card or certificate. Must explicitly cover both:
- Adult CPR
- Infant CPR (or "pediatric" — this covers infants)

**Accepted sources:** American Heart Association (BLS for Healthcare Providers), American Red Cross (CPR/AED for Professional Rescuers), or equivalent. Online-only CPR certifications without a hands-on skills component are NOT accepted by PCB.

**What to verify before uploading:**
- Not expired (check expiration date — most CPR certs are valid 2 years)
- "Adult and infant" competencies explicitly listed
- Issued by a recognized organization

**If the CPR cert is expired:**
The provider must renew before PCB will process the application. Most local hospitals and fire stations offer BLS renewal courses (typically 2–3 hours).

---

### Tasks 4, 5, 6: Client Evaluations

**What to collect from the provider:**
Three completed PCB Client Evaluation forms — one per family served. PCB provides the official form at pacertboard.org/doula. Download it and share with the provider to distribute to families.

**What to verify before uploading:**
- Three separate evaluations from three different families
- Each form must be signed by the client (family member), not the doula
- Forms can be handwritten or typed; PCB accepts both

**How to handle reluctant families:**
Remind the provider that PCB evaluations are brief (one page) and can be completed by email, mail, or in person. The provider gives the blank form to the family at or after the last visit.

---

## Task-by-Task Guide: Experienced Pathway

### Task 1: Proof of Active Practice

**What to collect from the provider:**
Documentation that they are currently working as a doula. Acceptable forms include:
- A letter from a doula agency confirming active contractor status
- An active listing on a doula directory (DoulaMatch, DONA member directory, etc.) — screenshot with URL
- Business registration or DBA filing if they operate independently
- A signed statement from a recent client confirming doula services (not a PCB evaluation form)

**What to verify before uploading:**
- Evidence is current (within the last 6 months preferred)
- Clearly identifies the provider by name

---

### Task 2: CPR Certification — Adult + Infant

Same requirements as Education/Training pathway Task 3 above.

---

### Tasks 3, 4, 5: Client Evaluations (within last year)

Same requirements as Education/Training pathway Tasks 4–6, with one additional requirement:

- All three evaluations must be from families served **within the last 12 months**
- Check the service date on each form before uploading

---

### Tasks 6, 7, 8: Letters of Recommendation (within last year)

**What to collect from the provider:**
Three letters of recommendation from families the doula served. These are **different** from client evaluations — they are free-form letters, not PCB forms.

**What to verify before uploading:**
- Three separate letters from three different families
- Each letter must be signed by the client (family member)
- Must be from families served within the **last 12 months** (PCB requirement for Experienced pathway)
- Letters should describe the doula's support during pregnancy, labor, or postpartum period
- No minimum length — even a brief sincere letter is acceptable

**How to help providers collect recommendation letters:**
Provide the provider with a sample request they can send to past clients:

> *"I am applying for my PCB Certified Perinatal Doula credential. Would you be willing to write a brief letter describing your experience working with me? It can be as short as a paragraph. I need it signed and dated. Thank you so much."*

---

## Submitting to PCB

Once all tasks are marked complete, submit the application to PCB at **pacertboard.org/doula** through their online application form or by mail.

**Before submitting, confirm:**
- [ ] All tasks marked complete in DoulaShield
- [ ] Training hours total ≥ 24 (Education/Training pathway)
- [ ] HIPAA training hours ≥ 1 (Education/Training pathway)
- [ ] CPR cert is current and not expired
- [ ] Three client evaluations collected and signed
- [ ] Experienced pathway: evaluations and letters all from within the last year
- [ ] PCB application fee paid (check current fee at pacertboard.org/doula)

**After submitting:**
Update the enrollment service status by clicking **Mark as Submitted to PCB** in DoulaShield. PCB typically processes applications within 4–6 weeks.

---

## Recording the PCB Certificate

When the provider receives their PCB certificate:

1. Go to **Admin → Enrollment Services** → open the service.
2. Upload the certificate file as a document on the service page.
3. Click **Mark PCB Complete** and enter the certificate issue date.
4. DoulaShield writes the certification date to the provider's profile (`pcb_last_certified_on`). The provider will see this date in their Settings page.

Note the certificate number in the task notes — it is required when completing CAQH ProView entry in Stage 2.

---

## Reference: Task Completion Checklist

| Task | Pathway | PCB Requirement |
|---|---|---|
| Training Certificate(s) | Education/Training | ≥ 24 total hours in CPD knowledge areas |
| HIPAA Training Certificate | Education/Training | ≥ 1 hour HIPAA/confidentiality |
| CPR Certification | Both | Current; adult + infant competencies |
| Client Evaluation #1 | Both | Signed by client |
| Client Evaluation #2 | Both | Signed by client |
| Client Evaluation #3 | Both | Signed by client; within last year (Experienced) |
| Proof of Active Practice | Experienced | Current evidence of active doula work |
| Letter of Recommendation #1 | Experienced | Signed by client; within last year |
| Letter of Recommendation #2 | Experienced | Signed by client; within last year |
| Letter of Recommendation #3 | Experienced | Signed by client; within last year |

---

## Stage 2: Enrollment (PROMISe™, Liability Insurance, CAQH ProView)

Stage 2 unlocks after the provider's PCB certification date is recorded. Create a Stage 2 service from Admin → Enrollment Services → + New Enrollment Service, select "Enrollment — Stage 2."

Eight tasks are auto-created:

### Type 1 vs Type 2 NPI — Quick Reference

Before starting the PROMISe™ application, confirm which NPI path applies. This determines Provider Type, the legal name/TIN source, and who must personally click Submit.

| | **Type 1 NPI — Individual Provider** | **Type 2 NPI — Agency / Group** |
|---|---|---|
| **PROMISe Provider Type** | 13 (Non-Traditional Provider) | 89 (Atypical Provider — Organization) |
| **Specialty** | 130 (Certified Doula) | 130 (Certified Doula) |
| **Tax ID** | Individual SSN or sole-proprietor EIN | Organization EIN (IRS SS-4 / CP575) |
| **NPI in NPPES** | Type 1 (individual 10-digit NPI) | Type 2 (group 10-digit NPI) |
| **Taxonomy code** | 176B00000X (Doula) | 176B00000X (Doula) |
| **Legal name** | As on W-9 Line 1 (individual name) | Organization legal name (as on EIN) |
| **Who clicks Submit** | **Provider must personally click Submit** — screen-share required | Authorized representative confirms verbally; DoulaShield staff may click Submit |
| **Attestation** | Individual reads terms, checks boxes, types legal name, clicks Submit | Organization's authorized representative is the legal certifier |
| **Credentials listed** | Provider's own PCB cert number + date | Each rostered doula's PCB cert number + date |
| **Insurance** | Individual policy | Agency group policy ($1M/$3M minimum) |
| **Ownership disclosure** | N/A | All owners ≥ 5% + managing employees |

### Task 1: W-9 Form

**What to collect:** A completed, signed IRS Form W-9. The provider's legal name and TIN (SSN or EIN) must exactly match what will be submitted to PROMISe™ and CAQH.

**What to verify:**
- Provider's legal name matches their government ID
- TIN is entered correctly (no blank fields)
- Signed and dated

**If the provider needs a W-9 form:** Download from IRS.gov — search "Form W-9". Sole proprietors use their SSN; those with an EIN should use it.

---

### Task 2: Government-Issued Photo ID

**What to collect:** A clear, unexpired government-issued photo ID. Acceptable: driver's license, state ID card, or passport.

**What to verify:**
- Not expired
- Photo clearly visible
- For a driver's license or state ID: include both front AND back

---

### Task 3: Liability Insurance Face Sheet

**What to collect:** The declarations page (face sheet) from a professional liability insurance policy. DoulaShield carries a group professional liability policy that covers all enrolled providers — contact the agency director to obtain the face sheet for the provider.

**What to verify the face sheet shows:**
- Insured name (provider or agency as named insured)
- Policy number
- Effective and expiration dates (must be current)
- Coverage limits: at minimum $1,000,000 per occurrence / $3,000,000 aggregate

**After uploading:** Record the policy expiration date in the notes field. DoulaShield will flag this for renewal.

---

### Task 4: PROMISe™ Type 13 Application (Medicaid)

**What PROMISe™ Type 13 is:** Pennsylvania's Medicaid provider enrollment application. Required to obtain a PROMISe™ Provider ID and bill any PA Medicaid MCO. The portal is **provider.ipx.pa.gov**.

See the Type 1 vs Type 2 NPI table above before starting — the Provider Type, legal name source, and attestation rules differ.

---

#### Individual Provider Path (Type 1 NPI)

Use the "Stage & Share" method: build the entire application first, then bring the provider in at the end for attestation. **The provider must personally read the compliance terms, check the acknowledgment boxes, type their legal name, and click Submit — you cannot click Submit on their behalf for an initial individual enrollment.**

**Prerequisite:** Confirm the provider's Type 1 NPI is active in NPPES and carries taxonomy code **176B00000X** (Doula). The PROMISe™ portal cross-checks the federal database in real time — a missing or mismatched taxonomy will stall progress on screen one.

**Step 1** — Navigate to provider.ipx.pa.gov. Create an application account if the provider is new. Select "Enroll as a New Provider."

**Step 2** — Select Provider Type **13** (Non-Traditional Provider), Specialty **130** (Certified Doula).

**Step 3** — Enter the provider's SSN (sole proprietors) or EIN if incorporated, exactly as it appears on their W-9. Do not mix SSN and EIN.

**Step 4** — For the primary service address, look up the ZIP+4 code at usps.com/zip4 before entering — the 9-digit format ensures the state-assigned 4-digit Service Location Code (0001) aligns with future MCO claims.

**Step 5** — On the credentials page, enter the PCB Certified Perinatal Doula (CPD) certificate number and exact issuance date. Upload a PDF scan. The name on the PCB certificate must match the NPI registration exactly.

**Step 6** — On the "Legal Billing Entity" screen, enter the name exactly as it appears on Line 1 of the provider's W-9. A mismatch with the IRS automated match routine forces a manual review and adds weeks to processing time.

**Step 7** — If the provider has any employment gaps of 30 days or more in the past 5 years, paste a one-sentence explanation into the notes field before advancing — unexplained gaps generate a DHS "Request for Information."

**Step 8** — Advance to the final attestation page. Screen-share with the provider. They read the compliance terms, check the boxes, type their legal name, and click Submit. **Copy the ATN immediately** — it is your only tracking token. Record it in the ATN field in the task row. Processing: 30–60 days.

---

#### Agency / Group Path (Type 2 NPI)

For agencies, DoulaShield may submit the application after the authorized representative has reviewed and confirmed the contents — organizational attestation does not require the same in-person provider click as individual enrollment.

**Step 1** — Navigate to provider.ipx.pa.gov. Select "Enroll as a New Provider."

**Step 2** — Select Provider Type **89** (Atypical Provider — Organization), Specialty **130** (Certified Doula).

**Step 3** — Enter the agency's EIN (from the IRS SS-4 letter / CP575). Enter the Type 2 group NPI from NPPES.

**Step 4** — Enter the agency's legal business address as the primary billing address. List the service counties in which the agency's doulas operate.

**Step 5** — On the credentials page, list each rostered doula's PCB certificate number and issuance date. Upload a consolidated PDF of all certificates.

**Step 6** — On the Liability Insurance screen, enter the agency's group policy carrier, policy number, and expiration date. Coverage must meet the minimum $1M per occurrence / $3M aggregate threshold.

**Step 7** — Complete the ownership/controlling interest disclosure for all owners with 5% or more ownership, plus all managing employees.

**Step 8** — Confirm application contents with the authorized representative, then submit. **Copy the ATN** into the ATN field in the task row. Processing: 30–60 days.

---

**What to upload:** Screenshot of the ATN confirmation page.

**ATN field:** Enter the ATN in the dedicated ATN field on the task row (not just the notes field) — it becomes visible to the provider on their Enrollment Status screen once the task is marked complete.

---

### Task 5: PROMISe™ Type 130 Application (CHIP)

**What PROMISe™ Type 130 is:** The CHIP (Children's Health Insurance Program) provider enrollment application. A separate enrollment type from Type 13 but submitted through the same PROMISe™ portal account. Required to bill CHIP-enrolled children under Keystone First CHIP, UPMC for You CHIP, and other CHIP MCOs. Submit this after the Type 13 ATN is in hand.

**How to apply:**

**Step 1** — Log back in to provider.ipx.pa.gov with the same account used for Type 13.

**Step 2** — Select "Add Enrollment Type" and choose Type **130** (CHIP Non-Traditional Provider), Specialty **130** (Certified Doula).

**Step 3** — Most fields pre-populate from the Type 13 application. Verify all fields are current — address, NPI, credentials, insurance — and correct any that have changed.

**Step 4** — Individual providers: bring the provider onto a screen-share for the final attestation page (same requirement as Type 13). Agency: submit after authorized representative confirmation.

**Step 5** — Copy the Type 130 ATN into the ATN field in the task row. It is a **separate** tracking token from the Type 13 ATN.

**What to upload:** Type 130 ATN confirmation screenshot.

---

### Tasks 6–8: CAQH ProView Enrollment

CAQH ProView enrollment is a three-task sequence: request Practice Manager access, wait for the provider to authorize DoulaShield, then complete and attest the profile.

**What CAQH ProView is:** The Council for Affordable Quality Healthcare (CAQH) ProView is a centralized credentialing database that all PA Medicaid MCOs use to verify provider credentials. Each provider must have an active, attested CAQH ProView profile. Attestation expires every 120 days and must be renewed.

**Task 6 — Request Practice Manager Access**
1. Sign in to DoulaShield's CAQH Practice Manager account at proview.caqh.org
2. Under the Providers tab, click "Add Provider" and search by the provider's NPI
3. Submit the access request — CAQH will notify the provider by email
4. Record the request date in the task notes

**Task 7 — Provider Authorizes DoulaShield**
The provider must log into their own CAQH ProView account and authorize DoulaShield under the Authorizations tab. Use the screen-share button to walk them through it. Without authorization, the admin cannot view or edit the provider's profile.

**Task 8 — Complete Profile & Provider Attests**
1. Log into CAQH Practice Manager and select the provider
2. Fill in all 12 sections: Personal Info, Address, Education, Postgraduate Training, Work History, Hospital Affiliations, Malpractice Insurance, Liability Insurance, References, Board Certifications, DEA/CDS, and Disclosure Questions
3. Edits are saved as "Suggested Import" — not live until the provider attests
4. Provider logs into their own CAQH ProView account and clicks "Attest"

**What to upload:** A screenshot of the CAQH ProView dashboard showing "Attested" status and the attestation date.

**What to record in notes:** The CAQH ProView ID (8-digit number shown on the dashboard). Enter this ID in the "Mark Enrollment Complete" modal — it is referenced in every MCO credentialing application in Stage 3.

**Attestation renewal reminder:** DoulaShield tracks the `caqh_last_attested_on` date on the provider's profile and alerts when renewal is approaching.

---

### Completing Stage 2

Once all 8 tasks are marked complete:
1. Click **Mark Enrollment Complete**
2. Enter the PROMISe™ enrollment date (date the application was submitted — actual approval arrives later but start the MCO process as soon as you have the ATN)
3. Enter the PROMISe™ Provider ID/ATN and CAQH ProView ID
4. Enter the liability insurance expiry date (from the face sheet)
5. Click **Complete Stage 2** — the provider's profile is updated and Stage 3 is unlocked

---

## Stage 3: MCO Contracting

Stage 3 unlocks after a Stage 2 enrollment service is marked complete for the provider. Create a Stage 3 service from Admin → Enrollment Services → + New Enrollment Service, select "MCO Contracting — Stage 3."

Ten tasks are auto-created: 2 shared documents and 1 task per MCO.

### Task 1: 5-Year Work History

**What to collect:** A document listing the provider's employment and self-employment history for the past 5 years.

**Required format:**
- Employer/agency name and address
- Start and end date (month and year)
- Position/role
- Reason for leaving (required for each position)
- For self-employment: describe as "Independent Doula — Self-employed"
- Gaps of 6+ months must be explained (e.g., "Parental leave," "Relocation")

Submit this document with every MCO credentialing application.

---

### Task 2: Resume / CV

**What to collect:** The provider's current resume or curriculum vitae, highlighting doula-related experience, trainings, and certifications.

**What it should include:**
- Full name and contact information
- Doula certifications (PCB, DONA, CAPPA, etc.)
- Training program completions with dates and hours
- Employment/contract work history as a doula
- Any relevant continuing education

---

### Tasks 3–10: MCO-Specific Applications + LOI

Each of the 8 MCOs has its own credentialing and contracting application. The process for each is similar:

**Letter of Intent (LOI) guidance:**
The LOI is a brief letter (1–2 paragraphs) from the agency stating:
- The provider's name, NPI, and CAQH ID
- Intent to contract as a rendering provider under the agency's billing NPI/Group NPI
- Services to be rendered (perinatal doula services — CPT T1032)
- The provider's service area (counties served)

Most MCOs accept a standard LOI template — draft one per MCO using the MCO's name and contracting department address.

**What to upload for each MCO task:**
- Completed credentialing application (PDF from the MCO's provider portal or mailed form)
- Signed LOI
- After contract is returned: the signed contract or approval letter

**Contract date field:** When you receive and sign the MCO contract, enter the contract signing date in the "Contract signed" field on the task row, then mark the task complete.

**MCO-specific notes:**

| MCO | Notes |
|---|---|
| AmeriHealth Caritas | Applications via AmeriHealth provider portal or PA CHIP/Medicaid provider relations |
| Keystone First | Submit through the Keystone First provider credentialing portal; include CHIP enrollment if applicable |
| UPMC For You | UPMC Medicaid provider enrollment via UPMC Health Plan's provider portal |
| Geisinger Health Plan | Geisinger Medical Management credentialing — request packet from provider relations |
| Highmark Wholecare | Highmark BCBS provider credentialing department — online portal or mail |
| UnitedHealthcare Community Plan | UHC Community Plan PA provider credentialing — submit via UHC provider portal |
| Aetna Better Health | Aetna Better Health PA — submit credentialing application via Availity portal (payer ID 23228) |
| Health Partners Plans | Health Partners Plans PA — contact provider relations for current credentialing packet |

**Expected timeline:** MCO credentialing typically takes 60–120 days per MCO. Submit all applications simultaneously to minimize total calendar time.

---

### Completing Stage 3

Once all 10 tasks are marked complete:
1. Click **Mark MCO Contracting Complete**
2. Enter the date the last MCO contract was finalized
3. Click **Complete Stage 3**

Individual MCO contract dates are preserved in each task's "Contract signed" field for reference.

---

## Provider Credential Status Summary

After all 3 stages are complete, the provider's Settings page shows:
- `pcb_last_certified_on` — PCB certification date (from Stage 1)
- `promise_last_enrolled_on` — PROMISe™ enrollment date (from Stage 2)
- `caqh_last_attested_on` — CAQH ProView attestation date (updated by provider in Settings)
- `liability_insurance_expires_on` — Liability insurance expiry (from Stage 2)
- `mco_contracts` — List of contracted MCOs with contract dates (managed in provider Settings)
